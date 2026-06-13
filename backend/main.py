from fastapi import FastAPI, HTTPException, UploadFile, File, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import chromadb
import ollama
import os
import shutil
import fitz 
from database import SessionLocal, Lead
from sqlalchemy.orm import Session

app = FastAPI(title="Real Estate RAG API - Multi-Tenant", version="2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

DB_PATH = "./chroma_db"
COLLECTION_NAME = "real_estate_docs"
LLM_MODEL = "qwen2.5:3b"

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

        response = ollama.chat(
            model=LLM_MODEL,
            messages=[
                {'role': 'system', 'content': system_prompt},
                {'role': 'user', 'content': request.question}
            ],
            stream=False 
        )
        return {"answer": response['message']['content']}
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

@app.get("/api/leads")
async def get_leads(
    x_tenant_id: str = Header(...), # Require the Tenant ID
    db: Session = Depends(get_db)
):
    try:
        # MULTI-TENANT FILTER: Only return leads for this specific tenant!
        leads = db.query(Lead).filter(Lead.tenant_id == x_tenant_id).order_by(Lead.created_at.desc()).all()
        return leads
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))