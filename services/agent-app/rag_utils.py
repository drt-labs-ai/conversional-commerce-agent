import os
from langchain_qdrant import Qdrant
from langchain_ollama import OllamaEmbeddings
from qdrant_client import QdrantClient

# Configuration
QDRANT_URL = os.getenv("QDRANT_URL", "http://qdrant:6333")
COLLECTION_NAME = "products"

def get_product_retriever():
    embeddings = OllamaEmbeddings(
        base_url=os.getenv("OLLAMA_BASE_URL", "http://ollama:11434"),
        model="nomic-embed-text"
    )
    
    client = QdrantClient(url=QDRANT_URL)
    
    vector_store = Qdrant(
        client=client,
        collection_name=COLLECTION_NAME,
        embeddings=embeddings,
    )
    
    return vector_store.as_retriever(search_kwargs={"k": 5})

def search_products_vector(query: str, k: int = 5):
    retriever = get_product_retriever()
    retriever.search_kwargs["k"] = k
    docs = retriever.invoke(query)
    # Format results
    results = []
    for doc in docs:
        results.append({
            "code": doc.metadata.get("code"),
            "name": doc.metadata.get("name"),
            "price": doc.metadata.get("price"),
            "description": doc.page_content # In Qdrant langchain integration content is stored
        })
    return results
