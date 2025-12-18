from rag_utils import search_products_vector
try:
    results = search_products_vector("camera")
    print(f"Found {len(results)} results.")
    for r in results:
        print(f"Result: {r}")
except Exception as e:
    print(f"Error: {e}")
