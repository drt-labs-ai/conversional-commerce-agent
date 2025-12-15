import os
import asyncio
import httpx
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
from langchain_ollama import OllamaEmbeddings

# Configuration
SAP_OCC_BASE_URL = os.getenv("SAP_OCC_BASE_URL", "https://host.docker.internal:9002/occ/v2")
QDRANT_URL = os.getenv("QDRANT_URL", "http://qdrant:6333")
MODEL_NAME = os.getenv("MODEL_NAME", "llama3")
COLLECTION_NAME = "products"

async def fetch_products(page_size=20, total_pages=5):
    """Fetch products from SAP OCC."""
    products = []
    async with httpx.AsyncClient(verify=False) as client:
        for page in range(total_pages):
            url = f"{SAP_OCC_BASE_URL}/powertools/products/search"
            params = {"pageSize": page_size, "currentPage": page, "fields": "FULL"}
            try:
                response = await client.get(url, params=params, timeout=10.0)
                if response.status_code == 200:
                    data = response.json()
                    products.extend(data.get("products", []))
                else:
                    print(f"Failed to fetch page {page}: {response.status_code}")
            except Exception as e:
                print(f"Error fetching page {page}: {e}")
    return products

def ingest_products():
    print("Starting product ingestion...")
    
    # 1. Fetch Products
    products = asyncio.run(fetch_products())
    print(f"Fetched {len(products)} products.")

    if not products:
        print("No products found. Exiting.")
        return

    # 2. Initialize Qdrant
    client = QdrantClient(url=QDRANT_URL)
    
    # Re-create collection
    client.recreate_collection(
        collection_name=COLLECTION_NAME,
        vectors_config=VectorParams(size=768, distance=Distance.COSINE), 
        # Note: nomic-embed-text/llama3 size varies. llama3 is 4096? nomic is 768.
        # We need to match the embedding model. Let's assume nomic-embed-text for embeddings.
    )

    # 3. Initialize Embeddings
    # We should use a specific embedding model, not the chat model
    embeddings_model = OllamaEmbeddings(
        base_url=os.getenv("OLLAMA_BASE_URL", "http://ollama:11434"),
        model="nomic-embed-text" 
    )

    points = []
    for idx, product in enumerate(products):
        code = product.get("code")
        name = product.get("name", "")
        description = product.get("description", "")
        summary = product.get("summary", "")
        
        text_to_embed = f"{name} {summary} {description}"
        
        try:
            vector = embeddings_model.embed_query(text_to_embed)
            
            # Helper to check dimension if unsure: 
            # if idx == 0: print(f"Embedding dimension: {len(vector)}")

            points.append(PointStruct(
                id=idx, # Can use hash of code
                vector=vector,
                payload={
                    "code": code,
                    "name": name,
                    "price": product.get("price", {}).get("formattedValue", "N/A"),
                    "description": description
                }
            ))
        except Exception as e:
            print(f"Error embedding product {code}: {e}")

    # 4. Upload
    if points:
        client.upsert(
            collection_name=COLLECTION_NAME,
            points=points
        )
        print(f"Successfully indexed {len(points)} products.")

if __name__ == "__main__":
    ingest_products()
