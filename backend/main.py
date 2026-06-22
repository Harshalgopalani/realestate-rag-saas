from fastapi import FastAPI, HTTPException, UploadFile, File, Depends, Header, Request, Query, Form
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import chromadb
import ollama
import os
from groq import Groq
import requests
import shutil
import fitz 
from database import SessionLocal, Lead
from sqlalchemy.orm import Session
from datetime import datetime
import sqlite3
import PyPDF2
import io
import os
from pydantic import BaseModel, Field
from typing import Optional

class LeadData(BaseModel):
    tenant: Optional[str] = Field(default="unknown_tenant")
    name: Optional[str] = Field(default="unknown_name")
    phone: Optional[str] = Field(default="unknown_phone")
    email: Optional[str] = Field(default="unknown_email")

app = FastAPI(title="Real Estate RAG API - Multi-Tenant", version="2.0")

# This automatically looks for the GROQ_API_KEY environment variable
groq_client = Groq()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

DB_PATH = "./chroma_db"
COLLECTION_NAME = "real_estate_docs"
LLM_MODEL = "llama3.2:1b"

os.makedirs("documents", exist_ok=True)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

class ChatRequest(BaseModel):
    question: str

class LeadCreate(BaseModel):
    name: str
    phone: str
    email: str

def chunk_text(text: str, chunk_size: int = 200, overlap: int = 50) -> list:
    words = text.split()
    chunks = []
    for i in range(0, len(words), chunk_size - overlap):
        chunk = " ".join(words[i:i + chunk_size])
        chunks.append(chunk)
    return chunks

# ---------------------------------------------------------
# LEAD MANAGEMENT SYSTEM (SQLITE)
# ---------------------------------------------------------

# ... existing code ...

# ---------------------------------------------------------
# ADMIN KNOWLEDGE BASE UPLOAD SYSTEM
# ---------------------------------------------------------
# We use a hardcoded master password so only YOU can upload files to the AI brain.
ADMIN_SECRET = "supersecret2026"

# 3. PDF Upload & Training Route
@app.post("/api/upload")
async def upload_document(
    file: UploadFile = File(...), 
    tenant_id: str = Form(...), 
    secret: str = Form(...),
    overwrite: str = Form("false") # ADDED: Overwrite flag
):
    if secret != ADMIN_SECRET:
        raise HTTPException(status_code=403, detail="Unauthorized")
        
    target_tenant = tenant_id.lower().replace(" ", "_")
    
    try:
        client = chromadb.PersistentClient(path=DB_PATH)
        collection = client.get_or_create_collection(name=COLLECTION_NAME)
        
        # ADDED: Wipe existing data if overwrite is checked
        if overwrite.lower() == "true":
            try:
                collection.delete(where={"tenant_id": target_tenant})
                print(f"[DB] Wiped previous data for tenant: {target_tenant}")
            except Exception as e:
                print(f"[DB] No existing data to delete or error: {e}")

        # Read the PDF
        reader = PyPDF2.PdfReader(io.BytesIO(await file.read()))
        text = ""
        for page in reader.pages:
            extracted = page.extract_text()
            if extracted:
                text += extracted + "\n"

        if not text.strip():
            return {"status": "error", "message": "Could not extract text from this PDF."}

        # 2. Chunk the text (1000 characters per chunk) so the AI can digest it
        chunks = [text[i:i+1000] for i in range(0, len(text), 1000)]
        print(f"[PROCESSING]: Broke PDF into {len(chunks)} chunks.")

        # 3. Save to ChromaDB Vector Database, tagged with the Tenant ID
        client = chromadb.PersistentClient(path=DB_PATH)
        collection = client.get_or_create_collection(name=COLLECTION_NAME)

        for i, chunk in enumerate(chunks):
            # Convert text into a mathematical vector using Ollama
            embedding = ollama.embeddings(model="nomic-embed-text", prompt=chunk)["embedding"]
            
            chunk_id = f"{tenant_id}_{file.filename}_chunk_{i}"
            
            # Save the chunk and STRICTLY tag it to this specific tenant
            collection.add(
                ids=[chunk_id],
                embeddings=[embedding],
                documents=[chunk],
                metadatas=[{"tenant_id": tenant_id}]
            )
            
        print(f"[UPLOAD SUCCESS]: {file.filename} vectorized for {tenant_id}!\n")
        return {"status": "success", "message": f"Successfully trained AI on {len(chunks)} chunks."}

    except Exception as e:
        print(f"[UPLOAD ERROR]: {e}")
        return {"status": "error", "message": str(e)}

# ---------------------------------------------------------

@app.post("/api/chat")
async def chat(request: Request):
    try:
        # 1. Read the raw request just like we did for leads
        data = await request.json()
        user_message = data.get("question", "")
        tenant_id = request.headers.get("x-tenant-id", "unknown_tenant")

        # 2. Search ChromaDB (RAG)
        client = chromadb.PersistentClient(path=DB_PATH)
        collection = client.get_collection(name=COLLECTION_NAME)
        
        query_embedding = ollama.embeddings(model="nomic-embed-text", prompt=user_message)["embedding"]
        
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=4,
            where={"tenant_id": tenant_id} 
        )
        
        context = ""
        if results['documents'] and results['documents'][0]:
            context = "\n\n---\n\n".join(results['documents'][0])
            
        system_prompt = f"""You are a helpful real estate assistant representing {tenant_id.replace('_', ' ').title()}. 
        You must answer ONLY using the context below. 
        If it's not in the context, say EXACTLY: "I do not have verified information regarding that."
        Keep your answers concise, professional, and easy to read.
        
        CONTEXT:
        {context}
        """

        # 3. Stream the AI Response
        response = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {'role': 'system', 'content': system_prompt},
                {'role': 'user', 'content': user_message}
            ],
            stream=True
        )
        
        # THE FIX: Only yield valid text, entirely ignoring 'None' or empty chunks
        def generate():
            for chunk in response:
                content = chunk.choices[0].delta.content
                if content is not None:
                    yield content
                    
        return StreamingResponse(generate(), media_type="text/event-stream")

    except Exception as e:
        print(f"[CHAT ERROR]: {e}")
        # Self-healing fallback message if the database is busy
        def error_generate():
            yield "I apologize, but I am having trouble connecting to my knowledge base right now. Please try asking again."
        return StreamingResponse(error_generate(), media_type="text/event-stream")


# ---------------------------------------------------------
# LEAD MANAGEMENT SYSTEM (SQLITE)
# ---------------------------------------------------------

def init_db():
    try:
        conn = sqlite3.connect("leads.db")
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS leads (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tenant_id TEXT,
                name TEXT,
                phone TEXT,
                email TEXT
            )
        ''')
        # Self-healing: If the timestamp column is missing, add it automatically
        try:
            cursor.execute('ALTER TABLE leads ADD COLUMN timestamp DATETIME DEFAULT CURRENT_TIMESTAMP')
        except sqlite3.OperationalError:
            pass # Column already exists, all good!
            
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"[DB INIT ERROR]: {e}")

# Run this immediately when the server starts
init_db()

# 2. Save the lead using RAW Request to bypass 422 errors completely
@app.post("/api/leads")
async def save_lead(request: Request):
    try:
        # Read the raw JSON from the frontend
        data = await request.json()
        
        print("\n--- INCOMING RAW LEAD DATA ---")
        print(data)
        print("------------------------------\n")
        
        # Safely extract variables
        tenant = data.get("tenant", "unknown_tenant")
        name = data.get("name", "unknown_name")
        phone = data.get("phone", "unknown_phone")
        email = data.get("email", "unknown_email")

        # Save to database
        conn = sqlite3.connect("leads.db")
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO leads (tenant_id, name, phone, email, timestamp) VALUES (?, ?, ?, ?, ?)",
            (tenant, name, phone, email, datetime.now().isoformat())
        )
        conn.commit()
        conn.close()
        
        print(f"[LEAD CAPTURED] {name} saved successfully!")
        return {"status": "success"}
        
    except Exception as e:
        print(f"[DB SAVE ERROR]: {e}")
        return {"status": "error", "message": str(e)}

# ... existing code ...



# Secret passcode to prevent random people from viewing the dashboard
DASHBOARD_SECRET = "beta123"

# ---------------------------------------------------------
# LEAD MANAGEMENT SYSTEM (SQLITE)
# ---------------------------------------------------------

# 1. Create the database table if it doesn't exist
def init_db():
    conn = sqlite3.connect("leads.db")
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS leads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tenant_id TEXT,
            name TEXT,
            phone TEXT,
            email TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

# Run this immediately when the server starts
init_db()

# 2. Save the lead when a buyer fills out the website form
# 2. The Bulletproof Route
@app.post("/api/leads")
async def save_lead(lead: LeadData):
    print("\n--- INCOMING LEAD DATA ---")
    print(f"Tenant: {lead.tenant}")
    print(f"Name: {lead.name}")
    print(f"Phone: {lead.phone}")
    print(f"Email: {lead.email}")
    print("--------------------------\n")

    try:
        conn = sqlite3.connect("leads.db")
        cursor = conn.cursor()
        
        cursor.execute(
            "INSERT INTO leads (tenant_id, name, phone, email, timestamp) VALUES (?, ?, ?, ?, ?)",
            (lead.tenant, lead.name, lead.phone, lead.email, datetime.now().isoformat())
        )
        conn.commit()
        conn.close()
        
        print(f"[LEAD CAPTURED] {lead.name} saved successfully!")
        return {"status": "success"}
        
    except Exception as e:
        print(f"[DB SAVE ERROR]: {e}")
        return {"status": "error", "message": str(e)}
# ... existing code ...

@app.get("/api/leads")
async def get_client_leads(tenant: str, secret: str):
    # Security check
    if secret != DASHBOARD_SECRET:
        raise HTTPException(status_code=403, detail="Unauthorized")
        
    try:
        # Connect to your SQLite database
        conn = sqlite3.connect("leads.db")
        cursor = conn.cursor()
        
        # Fetch only the leads for this specific client
        cursor.execute("SELECT name, phone, email, timestamp FROM leads WHERE tenant_id = ? ORDER BY timestamp DESC", (tenant,))
        rows = cursor.fetchall()
        conn.close()
        
        # Format the data for the frontend
        leads = [{"name": r[0], "phone": r[1], "email": r[2], "date": r[3]} for r in rows]
        return {"status": "success", "leads": leads}
        
    except Exception as e:
        print(f"[DB ERROR]: {e}")
        return {"status": "error", "leads": []}
    

# ---------------------------------------------------------
# WHATSAPP CLOUD API INTEGRATION
# ---------------------------------------------------------

# This is a secret password we make up. Meta will use this to verify it's talking to YOU.
WHATSAPP_VERIFY_TOKEN = "kukreja_secure_token_123" 

@app.get("/api/webhook")
async def verify_whatsapp_webhook(
    hub_mode: str = Query(None, alias="hub.mode"),
    hub_challenge: int = Query(None, alias="hub.challenge"),
    hub_verify_token: str = Query(None, alias="hub.verify_token")
):
    """
    Step 1: The Handshake. 
    When you configure Meta, they will send a GET request here. 
    If the token matches, we return the challenge number.
    """
    if hub_mode == "subscribe" and hub_verify_token == WHATSAPP_VERIFY_TOKEN:
        print("Meta Webhook Verified Successfully!")
        return hub_challenge
    
    raise HTTPException(status_code=403, detail="Invalid verification token")

# Load WhatsApp secrets from the server environment
WHATSAPP_TOKEN = os.getenv("WHATSAPP_TOKEN")
WHATSAPP_PHONE_ID = os.getenv("WHATSAPP_PHONE_ID")

# ---------------------------------------------------------
# THE MULTI-TENANT ROUTING ENGINE
# ---------------------------------------------------------
# In the future, this will be a database table. For now, it's an in-memory directory.
# We use your current test number ID and map it to Kukreja Paris.
TENANT_ROUTER = {
    os.getenv("WHATSAPP_PHONE_ID"): "kukreja_paris",
    # Example of how you will add your second client tomorrow:
    # "109876543212345": "godrej_properties" 
}

@app.post("/api/webhook")
async def receive_whatsapp_message(request: Request):
    try:
        body = await request.json()
        
        if "entry" in body and body["entry"][0]["changes"][0]["value"].get("messages"):
            message_info = body["entry"][0]["changes"][0]["value"]["messages"][0]
            
            # --- THE NEW DYNAMIC ROUTING LOGIC ---
            # Extract exactly WHICH agency number the buyer texted
            metadata = body["entry"][0]["changes"][0]["value"].get("metadata", {})
            business_phone_id = metadata.get("phone_number_id")
            
            # Look up the tenant in our directory
            target_tenant = TENANT_ROUTER.get(business_phone_id)
            
            if not target_tenant:
                print(f"[ROUTING ERROR] Unrecognized business phone ID: {business_phone_id}")
                return {"status": "success"} # Tell Meta 200 OK so they don't keep retrying

            if message_info["type"] == "text":
                user_phone = message_info["from"]
                user_message = message_info["text"]["body"]
                
                print(f"[WHATSAPP] Message routed to tenant: {target_tenant}")
                
                # --- 1. DYNAMIC RAG PIPELINE ---
                client = chromadb.PersistentClient(path=DB_PATH)
                collection = client.get_collection(name=COLLECTION_NAME)
                
                query_embedding = ollama.embeddings(model="nomic-embed-text", prompt=user_message)["embedding"]
                
                # The search is now dynamically filtered by whichever tenant was detected!
                results = collection.query(
                    query_embeddings=[query_embedding],
                    n_results=4,
                    where={"tenant_id": target_tenant} 
                )
                
                context = ""
                if results['documents'] and results['documents'][0]:
                    context = "\n\n---\n\n".join(results['documents'][0])
                    
                system_prompt = f"""You are a helpful real estate assistant representing {target_tenant.replace('_', ' ').title()}. 
                You must answer ONLY using the context below. 
                If it's not in the context, say EXACTLY: "I do not have verified information regarding that."
                Keep your answers concise, professional, and formatted nicely for a WhatsApp screen.
                
                CONTEXT:
                {context}
                """

                # --- 2. GENERATE ANSWER (Groq) ---
                response = groq_client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=[
                        {'role': 'system', 'content': system_prompt},
                        {'role': 'user', 'content': user_message}
                    ],
                    stream=False
                )
                
                ai_answer = response.choices[0].message.content

                # --- 3. DYNAMIC REPLY ---
                # We reply from the exact business number the user texted
                url = f"https://graph.facebook.com/v18.0/{business_phone_id}/messages"
                headers = {
                    "Authorization": f"Bearer {WHATSAPP_TOKEN}",
                    "Content-Type": "application/json"
                }
                payload = {
                    "messaging_product": "whatsapp",
                    "to": user_phone,
                    "type": "text",
                    "text": {"body": ai_answer}
                }
                
                requests.post(url, headers=headers, json=payload)
                print(f"[WHATSAPP] Dynamic reply sent successfully!")
                
        return {"status": "success"}
        
    except Exception as e:
        print(f"[WHATSAPP ERROR]: {e}")
        return {"status": "error"}