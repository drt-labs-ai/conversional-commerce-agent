import os
from langchain_qdrant import QdrantVectorStore
from langchain_huggingface import HuggingFaceEmbeddings
from qdrant_client import QdrantClient

# Configuration
QDRANT_URL = os.getenv("QDRANT_URL", "http://qdrant:6333")
COLLECTION_NAME = "products"

def get_product_retriever():
    embeddings = HuggingFaceEmbeddings(
        model_name=os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")
    )
    
    client = QdrantClient(url=QDRANT_URL)
    
    vector_store = QdrantVectorStore(
        client=client,
        collection_name=COLLECTION_NAME,
        embedding=embeddings,
    )
    
    return vector_store.as_retriever(search_kwargs={"k": 5})

def search_products_vector(query: str, k: int = 2):
    retriever = get_product_retriever()
    retriever.search_kwargs["k"] = k
    docs = retriever.invoke(query)
    # DEBUG: Print raw docs
    for i, d in enumerate(docs):
        print(f"DEBUG DOC {i}: {d}")
        
    # Format results
    results = []
    for doc in docs:
        content = doc.page_content
        if len(content) > 300:
            content = content[:300] + "..."
            
        results.append({
            "code": doc.metadata.get("code"),
            "name": doc.metadata.get("name"),
            "price": doc.metadata.get("price"),
            "description": content
        })
    return results
