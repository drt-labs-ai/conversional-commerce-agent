import asyncio
import os
import httpx
import sys

# Minimal OCC Client for debugging
class DebugOCCClient:
    def __init__(self):
        self.base_url = os.getenv("SAP_OCC_BASE_URL", "https://host.docker.internal:9002/occ/v2")
        self.verify = False

    async def create_cart(self):
        url = f"{self.base_url}/electronics/users/anonymous/carts"
        print(f"POST {url}")
        async with httpx.AsyncClient(verify=self.verify) as client:
            resp = await client.post(url)
            print(f"Create Status: {resp.status_code}")
            return resp.json()

    async def add_to_cart(self, cart_id, product_code):
        url = f"{self.base_url}/electronics/users/anonymous/carts/{cart_id}/entries"
        print(f"POST {url}")
        data = {"product": {"code": product_code}, "quantity": 1}
        async with httpx.AsyncClient(verify=self.verify) as client:
            resp = await client.post(url, json=data)
            print(f"Add Status: {resp.status_code}")
            print(f"Add Resp: {resp.text}")

async def main():
    client = DebugOCCClient()
    
    print("--- 1. Create Cart ---")
    cart_data = await client.create_cart()
    print(f"Cart Data: {cart_data}")
    
    code = cart_data.get("code")
    guid = cart_data.get("guid")
    
    print(f"\nCode: {code}")
    print(f"GUID: {guid}")
    
    # Test A: Add using Code
    print("\n--- 2. Try Adding with CODE ---")
    try:
        await client.add_to_cart(code, "1934793")
    except Exception as e:
        print(f"Error: {e}")

    # Test B: Add using GUID
    print("\n--- 3. Try Adding with GUID ---")
    try:
        await client.add_to_cart(guid, "1934793")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(main())
