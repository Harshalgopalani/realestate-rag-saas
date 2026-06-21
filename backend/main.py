from fastapi import FastAPI, HTTPException, UploadFile, File, Depends, Header, Request, Query
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
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
from pydantic import BaseModel
from typing import Optional

class LeadData(BaseModel):
    tenant: Optional[str] = "unknown_tenant"
    name: Optional[str] = "unknown_name"
    phone: Optional[str] = "unknown_phone"
    email: Optional[str] = "unknown_email"

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
# MULTI-TENANT ENDPOINTS
# Notice: x_tenant_id: str = Header(...) is required for all!
# ---------------------------------------------------------

@app.post("/api/upload")
async def upload_document(
    file: UploadFile = File(...), 
    x_tenant_id: str = Header(...)  # Require the Tenant ID
):
    try:
        file_location = f"documents/{x_tenant_id}_{file.filename}"
        with open(file_location, "wb+") as file_object:
            shutil.copyfileobj(file.file, file_object)
        
        text = ""
        if file.filename.endswith(".pdf"):
            doc = fitz.open(file_location)
            for page in doc:
                text += page.get_text().replace('\n', ' ') + " "
        elif file.filename.endswith(".txt"):
            with open(file_location, 'r', encoding='utf-8') as f:
                text = f.read()
        else:
            raise HTTPException(status_code=400, detail="Only PDF and TXT files supported.")

        if not text.strip():
            raise HTTPException(status_code=400, detail="Could not extract text.")

        chunks = chunk_text(text)
        client = chromadb.PersistentClient(path=DB_PATH)
        collection = client.get_or_create_collection(name=COLLECTION_NAME)
        
        # ---------------------------------------------------------
        # NEW: THE GHOST DATA SWEEPER
        # Wipe the tenant's existing memory before training the new file
        # ---------------------------------------------------------
        try:
            collection.delete(where={"tenant_id": x_tenant_id})
            print(f"Cleared old knowledge base for tenant: {x_tenant_id}")
        except Exception as e:
            print(f"No existing data to clear.")
        # ---------------------------------------------------------

        for i, chunk in enumerate(chunks):
            embedding = ollama.embeddings(model="nomic-embed-text", prompt=chunk)["embedding"]
            
            # Because we wiped the old data, we can safely use .add()
            collection.add(
                ids=[f"{x_tenant_id}_{file.filename}_{i}"],
                embeddings=[embedding],
                documents=[chunk],
                metadatas=[{"source": file.filename, "tenant_id": x_tenant_id}] 
            )
            
        return {"status": "success", "message": f"Processed {file.filename}. The bot's memory is fully refreshed!"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/chat")
async def chat_endpoint(
    request: ChatRequest, 
    x_tenant_id: str = Header(...) # Require the Tenant ID
):
    try:
        client = chromadb.PersistentClient(path=DB_PATH)
        collection = client.get_collection(name=COLLECTION_NAME)
        
        query_embedding = ollama.embeddings(model="nomic-embed-text", prompt=request.question)["embedding"]
        
        # MULTI-TENANT FILTER: Only search vectors that match this tenant!
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=4,
            where={"tenant_id": x_tenant_id} 
        )
        
        context = ""
        if results['documents'] and results['documents'][0]:
            context = "\n\n---\n\n".join(results['documents'][0])
            
        system_prompt = f"""You are a helpful real estate assistant. 
        You must answer ONLY using the context below. 
        If it's not in the context, say EXACTLY: "I do not have verified information regarding that."
        
        CONTEXT:
        {context}
        """

        # ---------------------------------------------------------
        # NEW: THE STREAMING ENGINE
        # This function yields words instantly as they are generated
        # ---------------------------------------------------------
        # ---------------------------------------------------------
        # THE GROQ LPU STREAMING ENGINE
        # ---------------------------------------------------------
        def generate_response():
            stream = groq_client.chat.completions.create(
                model="llama-3.3-70b-versatile", # A massive, genius-level model
                messages=[
                    {'role': 'system', 'content': system_prompt},
                    {'role': 'user', 'content': request.question}
                ],
                stream=True
            )
            for chunk in stream:
                # Groq formats their chunks slightly differently than Ollama
                if chunk.choices[0].delta.content is not None:
                    yield chunk.choices[0].delta.content

        # Wrap the generator in a continuous HTTP stream
        return StreamingResponse(generate_response(), media_type="text/plain")

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/leads")
async def create_lead(
    lead: LeadCreate, 
    x_tenant_id: str = Header(...), # Require the Tenant ID
    db: Session = Depends(get_db)
):
    try:
        # MULTI-TENANT LOCK: Save the lead tied to the specific tenant
        db_lead = Lead(tenant_id=x_tenant_id, name=lead.name, phone=lead.phone, email=lead.email)
        db.add(db_lead)
        db.commit()
        return {"status": "success"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))



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
@app.post("/api/leads")
async def save_lead(lead: LeadData):
    print(f"--- INCOMING LEAD DATA ---")
    print(f"Tenant: {lead.tenant}")
    print(f"Name: {lead.name}")
    print(f"Phone: {lead.phone}")
    print(f"Email: {lead.email}")
    print(f"--------------------------")

    try:
        conn = sqlite3.connect("leads.db")
        cursor = conn.cursor()
        
        cursor.execute(
            "INSERT INTO leads (tenant_id, name, phone, email, timestamp) VALUES (?, ?, ?, ?, ?)",
            (lead.tenant, lead.name, lead.phone, lead.email, datetime.now().isoformat())
        )
        conn.commit()
        conn.close()
        
        print(f"[LEAD CAPTURED] {lead.name} saved for tenant: {lead.tenant}")
        return {"status": "success"}
        
    except Exception as e:
        print(f"[DB SAVE ERROR]: {e}")
        return {"status": "error", "message": str(e)}

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