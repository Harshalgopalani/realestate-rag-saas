from fastapi import FastAPI, HTTPException, UploadFile, File, Form, Query, Request, BackgroundTasks
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional
import chromadb
import ollama
import os
import requests
import PyPDF2
import io
import sqlite3
from datetime import datetime
from groq import Groq

# ---------------------------------------------------------
# INITIALIZATION
# ---------------------------------------------------------

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
ADMIN_SECRET = "supersecret2026"
DASHBOARD_SECRET = "beta123"

os.makedirs("documents", exist_ok=True)

# ---------------------------------------------------------
# DATA MODELS
# ---------------------------------------------------------

class LeadData(BaseModel):
    tenant: Optional[str] = Field(default="unknown_tenant")
    name: Optional[str] = Field(default="unknown_name")
    phone: Optional[str] = Field(default="unknown_phone")
    email: Optional[str] = Field(default="unknown_email")

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
# LEAD MANAGEMENT SYSTEM (SQLITE) & CRM
# ---------------------------------------------------------

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

def push_to_crm(lead_data: dict):
    # FIXED: Removed the duplicated URL schema
    crm_webhook_url = "https://webhook.site/bacf13f9-a8eb-4dd8-8265-fd566a13b5bc"
    
    payload = {
        "source": "AI_Property_Bot",
        "tenant_id": lead_data.get("tenant", "unknown"),
        "lead_name": lead_data.get("name", ""),
        "lead_phone": lead_data.get("phone", ""),
        "lead_email": lead_data.get("email", ""),
        "status": "New Lead Captured"
    }
    
    try:
        response = requests.post(crm_webhook_url, json=payload, timeout=5)
        print(f"[CRM PUSH SUCCESS] Status Code: {response.status_code}")
    except Exception as e:
        print(f"[CRM PUSH FAILED] Error: {e}")

@app.post("/api/leads")
async def save_lead(request: Request, background_tasks: BackgroundTasks):
    data = await request.json()
    
    lead_tenant = data.get("tenant", "unknown_tenant")
    lead_name = data.get("name", "unknown_name")
    lead_phone = data.get("phone", "unknown_phone")
    lead_email = data.get("email", "unknown_email")

    print("\n--- INCOMING RAW LEAD DATA ---")
    print(data)
    print("------------------------------\n")

    try:
        conn = sqlite3.connect("leads.db")
        cursor = conn.cursor()
        
        cursor.execute(
            "INSERT INTO leads (tenant_id, name, phone, email, timestamp) VALUES (?, ?, ?, ?, ?)",
            (lead_tenant, lead_name, lead_phone, lead_email, datetime.now().isoformat())
        )
        conn.commit()
        conn.close()
        
        print(f"[LEAD CAPTURED] {lead_name} saved successfully!")
        
        # Push to CRM invisibly in the background
        background_tasks.add_task(push_to_crm, data)
        
        return {"status": "success"}
        
    except Exception as e:
        print(f"[DB SAVE ERROR]: {e}")
        return {"status": "error", "message": str(e)}

@app.get("/api/leads")
async def get_client_leads(tenant: str, secret: str):
    if secret != DASHBOARD_SECRET:
        raise HTTPException(status_code=403, detail="Unauthorized")
        
    try:
        conn = sqlite3.connect("leads.db")
        cursor = conn.cursor()
        
        cursor.execute("SELECT name, phone, email, timestamp FROM leads WHERE tenant_id = ? ORDER BY timestamp DESC", (tenant,))
        rows = cursor.fetchall()
        conn.close()
        
        leads = [{"name": r[0], "phone": r[1], "email": r[2], "date": r[3]} for r in rows]
        return {"status": "success", "leads": leads}
        
    except Exception as e:
        print(f"[DB ERROR]: {e}")
        return {"status": "error", "leads": []}

# ---------------------------------------------------------
# ADMIN KNOWLEDGE BASE UPLOAD SYSTEM
# ---------------------------------------------------------

@app.post("/api/upload")
async def upload_document(
    file: UploadFile = File(...), 
    tenant_id: str = Form(...), 
    secret: str = Form(...),
    overwrite: str = Form("false") 
):
    if secret != ADMIN_SECRET:
        raise HTTPException(status_code=403, detail="Unauthorized")
        
    target_tenant = tenant_id.lower().replace(" ", "_")
    
    try:
        client = chromadb.PersistentClient(path=DB_PATH)
        collection = client.get_or_create_collection(name=COLLECTION_NAME)
        
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

        # Chunk the text
        # FIX: Use the smart chunking function you wrote earlier!
        chunks = chunk_text(text, chunk_size=250, overlap=50)
        print(f"[PROCESSING]: Broke PDF into {len(chunks)} chunks.")

        for i, chunk in enumerate(chunks):
            embedding = ollama.embeddings(model="nomic-embed-text", prompt=chunk)["embedding"]
            chunk_id = f"{tenant_id}_{file.filename}_chunk_{i}"
            
            collection.add(
                ids=[chunk_id],
                embeddings=[embedding],
                documents=[chunk],
                # FIX: Use target_tenant here so the overwrite function can find it later!
                metadatas=[{"tenant_id": target_tenant}] 
            )
            
        print(f"[UPLOAD SUCCESS]: {file.filename} vectorized for {tenant_id}!\n")
        return {"status": "success", "message": f"Successfully trained AI on {len(chunks)} chunks."}

    except Exception as e:
        print(f"[UPLOAD ERROR]: {e}")
        return {"status": "error", "message": str(e)}

# ---------------------------------------------------------
# WEB CHAT SYSTEM
# ---------------------------------------------------------

@app.post("/api/chat")
async def chat(request: Request):
    try:
        data = await request.json()
        user_message = data.get("question", "")
        
        # BUG FIX: Force lowercase and underscores so typos in URLs don't break the database lookup
        raw_tenant = request.headers.get("x-tenant-id", "unknown_tenant")
        tenant_id = raw_tenant.lower().replace(" ", "_")

        client = chromadb.PersistentClient(path=DB_PATH)
        # BUG FIX: Use get_or_create so it doesn't crash on a completely fresh server install
        collection = client.get_or_create_collection(name=COLLECTION_NAME)
        
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

        response = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {'role': 'system', 'content': system_prompt},
                {'role': 'user', 'content': user_message}
            ],
            stream=True
        )
        
        def generate():
            for chunk in response:
                content = chunk.choices[0].delta.content
                if content is not None:
                    yield content
                    
        return StreamingResponse(generate(), media_type="text/event-stream")

    except Exception as e:
        print(f"[CHAT ERROR]: {e}")
        def error_generate():
            yield "I apologize, but I am having trouble connecting to my knowledge base right now. Please try asking again."
        return StreamingResponse(error_generate(), media_type="text/event-stream")

# ---------------------------------------------------------
# WHATSAPP CLOUD API INTEGRATION
# ---------------------------------------------------------

WHATSAPP_VERIFY_TOKEN = "kukreja_secure_token_123" 

@app.get("/api/webhook")
async def verify_whatsapp_webhook(
    hub_mode: str = Query(None, alias="hub.mode"),
    hub_challenge: int = Query(None, alias="hub.challenge"),
    hub_verify_token: str = Query(None, alias="hub.verify_token")
):
    if hub_mode == "subscribe" and hub_verify_token == WHATSAPP_VERIFY_TOKEN:
        print("Meta Webhook Verified Successfully!")
        return hub_challenge
    
    raise HTTPException(status_code=403, detail="Invalid verification token")

WHATSAPP_TOKEN = os.getenv("WHATSAPP_TOKEN")
# Use an empty string fallback so it never creates a "None" key
phone_id_key = os.getenv("WHATSAPP_PHONE_ID", "default_number")
TENANT_ROUTER = {
    phone_id_key: "kukreja_paris",
}

@app.post("/api/webhook")
async def receive_whatsapp_message(request: Request):
    try:
        body = await request.json()
        
        if "entry" in body and body["entry"][0]["changes"][0]["value"].get("messages"):
            message_info = body["entry"][0]["changes"][0]["value"]["messages"][0]
            
            metadata = body["entry"][0]["changes"][0]["value"].get("metadata", {})
            business_phone_id = metadata.get("phone_number_id")
            
            target_tenant = TENANT_ROUTER.get(business_phone_id)
            
            if not target_tenant:
                print(f"[ROUTING ERROR] Unrecognized business phone ID: {business_phone_id}")
                return {"status": "success"} 

            if message_info["type"] == "text":
                user_phone = message_info["from"]
                user_message = message_info["text"]["body"]
                
                print(f"[WHATSAPP] Message routed to tenant: {target_tenant}")
                
                client = chromadb.PersistentClient(path=DB_PATH)
                # BUG FIX: Prevent crash if no PDFs have been uploaded yet
                collection = client.get_or_create_collection(name=COLLECTION_NAME)
                
                query_embedding = ollama.embeddings(model="nomic-embed-text", prompt=user_message)["embedding"]
                
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

                response = groq_client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=[
                        {'role': 'system', 'content': system_prompt},
                        {'role': 'user', 'content': user_message}
                    ],
                    stream=False
                )
                
                ai_answer = response.choices[0].message.content

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