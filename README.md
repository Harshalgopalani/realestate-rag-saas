# 🏢 Real Estate RAG Automator: 24/7 Lead Qualification SaaS

**Autonomous Property Inquiry & Customer Qualification Pipeline**

## 📌 Executive Summary
In real estate sales, time-to-contact is the primary driver of conversion. Leads generated after business hours or during high-volume periods often go cold due to delayed responses. **The Real Estate RAG Automator** is a Retrieval-Augmented Generation (RAG) SaaS backend built to solve this bottleneck. It instantly ingests customer inquiries, retrieves exact property specifications from a vector database, and generates hyper-personalized, accurate responses 24/7—while simultaneously qualifying the lead for human agents.

## 🏗️ System Architecture
This application is designed as a scalable, low-latency microservice using open-source and high-performance infrastructure:

*   **API Gateway (FastAPI):** High-throughput asynchronous REST API that handles incoming customer queries from webhooks (e.g., WhatsApp Business, Website Chatbots).
*   **Knowledge Base (ChromaDB):** A localized vector database embedding live property listings, floor plans, pricing tiers, and neighborhood amenities.
*   **Inference Engine (Groq API):** Utilizes Groq's LPU for near-instantaneous LLM inference, keeping response latency under 500ms to mimic live human chat.
*   **Lead Routing:** Extracts intent from the user query (e.g., "ready to buy" vs. "just browsing") and tags the payload before handing it off to human channel partners.

## 💼 Business Impact
*   **Zero-Latency Initial Contact:** Reduces average response time from hours to milliseconds, capitalizing on the buyer's peak intent window.
*   **Automated Qualification:** Pre-screens leads on budget, preferred location, and timeline, freeing up human agents to focus strictly on high-probability closures.
*   **Always-On Availability:** Captures and nurtures leads generated on weekends or after hours without increasing headcount.

## 🛠️ Technology Stack
*   **Backend Framework:** Python 3.11, FastAPI, Pydantic (Strict Data Validation)
*   **AI / RAG:** ChromaDB (Vector Store), Groq API (Inference), LangChain/LlamaIndex (Orchestration)
*   **Testing & CI/CD:** Pytest, GitHub Actions, Docker

## 🚀 Quick Start (Local Development)
1. Clone the repository: `git clone https://github.com/YourUsername/real-estate-rag-automator.git`
2. Install dependencies: `pip install -r requirements.txt`
3. Set up environment variables: Copy `.env.example` to `.env` and add your `GROQ_API_KEY`.
4. Run the FastAPI server: `uvicorn src.api.main:app --reload`
5. Access the interactive API docs at `http://localhost:8000/docs`
