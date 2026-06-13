import fitz  # PyMuPDF
import chromadb
import ollama
import os

# 1. Configuration - Pointing to our new Text file
FILE_PATH = "documents/brochure_text.txt"
DB_PATH = "./chroma_db"
COLLECTION_NAME = "real_estate_docs"

def extract_text(file_path):
    """Reads either a PDF or a TXT file."""
    print(f"Reading {file_path}...")
    
    if file_path.endswith('.pdf'):
        doc = fitz.open(file_path)
        text = ""
        for page in doc:
            text += page.get_text().replace('\n', ' ') + " "
        return text
        
    elif file_path.endswith('.txt'):
        with open(file_path, 'r', encoding='utf-8') as file:
            return file.read()
    else:
        print("Unsupported file format!")
        return ""

def chunk_text(text, chunk_size=100, overlap=20):
    """Splits text into chunks. Made smaller for our TXT file."""
    print("Splitting text into chunks...")
    words = text.split()
    chunks = []
    for i in range(0, len(words), chunk_size - overlap):
        chunk = " ".join(words[i:i + chunk_size])
        chunks.append(chunk)
    print(f"SUCCESS: Created {len(chunks)} chunks.")
    return chunks

def store_in_chromadb(chunks):
    """Stores the chunks in the Vector DB."""
    print("Connecting to ChromaDB...")
    client = chromadb.PersistentClient(path=DB_PATH)
    
    # Delete the old empty collection to start fresh
    try:
        client.delete_collection(name=COLLECTION_NAME)
    except:
        pass
        
    collection = client.create_collection(name=COLLECTION_NAME)
    
    print(f"Generating embeddings for {len(chunks)} chunks...")
    for i, chunk in enumerate(chunks):
        response = ollama.embeddings(model="nomic-embed-text", prompt=chunk)
        embedding = response["embedding"]
        
        collection.add(
            ids=[f"text_chunk_{i}"],
            embeddings=[embedding],
            documents=[chunk],
            metadatas=[{"source": FILE_PATH}]
        )
    print("\nSUCCESS: Data stored in ./chroma_db")

if __name__ == "__main__":
    if not os.path.exists(FILE_PATH):
        print(f"CRITICAL ERROR: Cannot find the file at {FILE_PATH}")
    else:
        raw_text = extract_text(FILE_PATH)
        if len(raw_text.strip()) > 0:
            text_chunks = chunk_text(raw_text)
            store_in_chromadb(text_chunks)
        else:
            print("CRITICAL ERROR: No text found.")