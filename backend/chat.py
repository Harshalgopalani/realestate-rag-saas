import chromadb
import ollama

# 1. Configuration
DB_PATH = "./chroma_db"
COLLECTION_NAME = "real_estate_docs"
LLM_MODEL = "qwen2.5:3b"

def retrieve_context(query, n_results=3):
    """Searches the database for the most relevant chunks based on the user's question."""
    client = chromadb.PersistentClient(path=DB_PATH)
    collection = client.get_collection(name=COLLECTION_NAME)
    
    # Convert the user's question into an embedding to match against the database
    query_embedding = ollama.embeddings(model="nomic-embed-text", prompt=query)["embedding"]
    
    # Query ChromaDB
    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=n_results
    )
    
    # Combine the top results into a single string
    retrieved_texts = results['documents'][0]
    return "\n\n---\n\n".join(retrieved_texts)

def ask_bot(question):
    """Constructs the prompt and streams the response from Ollama."""
    print("\n[Searching Documents...]")
    context = retrieve_context(question)
    
    # The System Prompt: This is the brain of your SaaS guardrails.
    system_prompt = f"""You are a helpful real estate assistant. 
    You must answer the user's question ONLY using the context provided below. 
    If the context does not contain the answer, say EXACTLY: "I do not have verified information regarding that."
    Never guess prices, dates, or amenities.
    
    CONTEXT:
    {context}
    """

    print("\n[Generating Answer...]\n")
    # Call Ollama LLM
    stream = ollama.chat(
        model=LLM_MODEL,
        messages=[
            {'role': 'system', 'content': system_prompt},
            {'role': 'user', 'content': question}
        ],
        stream=True
    )
    
    # Stream the output letter by letter like ChatGPT
    for chunk in stream:
        print(chunk['message']['content'], end='', flush=True)
    print("\n")

if __name__ == "__main__":
    print("Welcome to the Real Estate RAG Chatbot.")
    print("Type 'quit' to exit.")
    
    while True:
        user_input = input("\nYou: ")
        if user_input.lower() in ['quit', 'exit']:
            break
        ask_bot(user_input)