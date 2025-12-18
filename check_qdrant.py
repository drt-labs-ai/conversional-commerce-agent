from qdrant_client import QdrantClient; print(QdrantClient('http://qdrant:6333').count('products').count)
