# Conversational Commerce Agent

A local, containerized AI Chatbot for SAP Commerce, built with **LangGraph**, **Ollama**, and the **Model Context Protocol (MCP)**. 

This agentic system provides a conversational interface to discovering products and managing a shopping cart on a local SAP Commerce instance, demonstrating a fully private, local RAG and tool-use architecture.

---

## 🏗 System Architecture

The system is composed of Docker services orchestrated via Docker Compose.

```mermaid
graph TD
    User[User via Chainlit UI] <--> AgentApp[Agent App (LangGraph)]
    
    subgraph "Docker Network (commerce-net)"
        AgentApp -->|LLM Inference| Ollama[Ollama (Llama 3)]
        AgentApp -->|Vector Search| Qdrant[Qdrant (Vector DB)]
        AgentApp -->|State Persistence| Redis[Redis]
        
        AgentApp -->|MCP Protocol (SSE)| MCPServer[SAP MCP Server]
    end
    
    subgraph "External/Host"
        MCPServer -->|OCC REST APIs| SAP[SAP Commerce (Localhost)]
        Qdrant -.->|Ingestion| SAP
    end
```

### Components

1.  **Agent App (`services/agent-app`)**
    *   **Framework**: LangGraph + LangChain.
    *   **Interface**: Chainlit.
    *   **Agents**:
        *   `Supervisor`: Routes tasks to specialized agents.
        *   `SearchAgent`: Handles product discovery using Vector Search (RAG) and structured SAP Search.
        *   `CartAgent`: Manages cart operations (Add, View, Checkout).
2.  **SAP MCP Server (`services/sap-mcp-server`)**
    *   **Protocol**: Model Context Protocol (MCP) over SSE (Server-Sent Events).
    *   **Function**: Bridges the generic AI world with SAP Commerce OCC APIs.
    *   **Tools Exposed**: `search_products`, `get_product_details`, `create_cart`, `add_to_cart`, `get_cart`, `place_order`.
3.  **Data Persistence & Intelligence**
    *   **Ollama**: Local implementation of Llama 3 for reasoning and embedding.
    *   **Qdrant**: Vector database storing product embeddings for semantic search.
    *   **Redis**: Stores conversation history and agent state checkpoints.

---

## 🛠 Prerequisites

*   **Docker Desktop** (with Docker Compose)
*   **SAP Commerce** (Hybris) running locally (Default: `https://localhost:9002/occ/v2`)
    *   *Note: Ensure your `host.docker.internal` allows connection from containers.*
*   **Git**

## 🚀 Build & Run

### 1. Clone & Configure
```bash
git clone https://github.com/drt-labs-ai/conversional-commerce-agent.git
cd conversional-commerce-agent
```

Check the `.env` file and update SAP Commerce credentials if necessary:
```env
SAP_OCC_BASE_URL=https://host.docker.internal:9002/occ/v2
SAP_OCC_USERNAME=test_user
SAP_OCC_PASSWORD=test_password
```

### 2. Start Services
```bash
docker-compose up -d --build
```

### 3. Initialize Models (First Run Only)
Pull the required LLM models into the Ollama container:
```bash
docker exec -it ollama ollama pull llama3
docker exec -it ollama ollama pull nomic-embed-text
```

### 4. Ingest Product Data
Index your SAP Commerce products into the Vector Database (RAG):
```bash
docker exec -it agent-app python /app/scripts/ingest_products.py
```

---

## 💡 Usage

Open your browser to: **[http://localhost:8000](http://localhost:8000)**

### Example Scenarios

#### Product Discovery (RAG + Search)
> **User**: "I need a heavy duty cordless drill."
>
> **Agent**: *Uses Vector Search to find semantically relevant products descriptions, then queries SAP for real-time price/stock.*

#### Shopping Cart (Transactional)
> **User**: "Add the Makita drill to my cart."
>
> **Agent**: *Creates a cart (if none exists) and adds the item using SAP OCC APIs.*

#### Checkout
> **User**: "I'm ready to checkout."
>
> **Agent**: *Sets delivery address/mode and places the order.*

---

## 📂 Project Structure

```text
├── services/
│   ├── agent-app/          # Main Chatbot & LangGraph Logic
│   │   ├── agent_graph.py  # Agent definitions (Supervisor, Search, Cart)
│   │   ├── app.py          # Chainlit UI Entry point
│   │   └── rag_utils.py    # Vector Search utils
│   └── sap-mcp-server/     # Custom Tool Provider
│       ├── server.py       # MCP Server (FastAPI/SSE)
│       └── occ_client.py   # SAP Commerce API Client
├── scripts/
│   └── ingest_products.py  # Data Pipeline for RAG
├── docker-compose.yml      # Orchestration
└── .env                    # Configuration
```

## 🛡 License
MIT
