import os
import httpx
from typing import Optional, Dict, Any, List

class SAPOCCClient:
    def __init__(self):
        self.base_url = os.getenv("SAP_OCC_BASE_URL", "https://localhost:9002/occ/v2")
        self.username = os.getenv("SAP_OCC_USERNAME", "anonymous")
        self.password = os.getenv("SAP_OCC_PASSWORD")
        # In a real scenario, you'd manage OAuth2 tokens here.
        # For this local setup, we might assume Basic Auth or just 'anonymous' for some calls,
        # but for Cart/Order we need a user.
        # We'll use a placeholder user 'current' if we have a valid token, or a specific userId.
        self.user_id = "current" 
        self.client = httpx.AsyncClient(verify=False) # Local certs are often self-signed

    async def _get_headers(self) -> Dict[str, str]:
        # TODO: Implement full OAuth2 flow if needed.
        # For now, we assume we might be using Basic Auth or passing a token if available.
        # If using 'hybris' 'nimda' etc, we might need Basic Auth header.
        # auth = httpx.BasicAuth(self.username, self.password)
        # return {"Authorization": auth.build_auth_header()}
        return {
            "Content-Type": "application/json",
            "Accept": "application/json"
        }

    async def search_products(self, query: str, pageSize: int = 5, currentPage: int = 0) -> Dict[str, Any]:
        url = f"{self.base_url}/powertools/products/search"
        params = {
            "query": query,
            "pageSize": pageSize,
            "currentPage": currentPage,
            "fields": "FULL"
        }
        response = await self.client.get(url, params=params, headers=await self._get_headers())
        response.raise_for_status()
        return response.json()

    async def get_product_details(self, product_code: str) -> Dict[str, Any]:
        url = f"{self.base_url}/powertools/products/{product_code}"
        params = {"fields": "FULL"}
        response = await self.client.get(url, params=params, headers=await self._get_headers())
        response.raise_for_status()
        return response.json()

    async def create_cart(self) -> Dict[str, Any]:
        # For anonymous: /users/anonymous/carts
        # For authenticated: /users/current/carts
        # We'll default to anonymous for this demo if no refined auth is present,
        # or assume we are 'current' with a token.
        # Let's try creating a cart for 'anonymous' first to be safe for local dev without complex auth.
        user = "anonymous"
        url = f"{self.base_url}/powertools/users/{user}/carts"
        response = await self.client.post(url, headers=await self._get_headers())
        response.raise_for_status()
        return response.json()

    async def add_to_cart(self, cart_id: str, product_code: str, quantity: int = 1) -> Dict[str, Any]:
        user = "anonymous" # align with create_cart
        url = f"{self.base_url}/powertools/users/{user}/carts/{cart_id}/entries"
        data = {
            "product": {"code": product_code},
            "quantity": quantity
        }
        response = await self.client.post(url, json=data, headers=await self._get_headers())
        response.raise_for_status()
        return response.json()

    async def get_cart(self, cart_id: str) -> Dict[str, Any]:
        user = "anonymous"
        url = f"{self.base_url}/powertools/users/{user}/carts/{cart_id}"
        params = {"fields": "FULL"}
        response = await self.client.get(url, params=params, headers=await self._get_headers())
        response.raise_for_status()
        return response.json()

    async def set_delivery_address(self, cart_id: str, address: Dict[str, Any]) -> Dict[str, Any]:
        user = "anonymous"
        url = f"{self.base_url}/powertools/users/{user}/carts/{cart_id}/addresses/delivery"
        response = await self.client.post(url, json=address, headers=await self._get_headers())
        response.raise_for_status()
        return response.json()

    async def set_delivery_mode(self, cart_id: str, delivery_mode: str) -> Dict[str, Any]:
        user = "anonymous"
        url = f"{self.base_url}/powertools/users/{user}/carts/{cart_id}/deliverymode"
        params = {"deliveryModeId": delivery_mode}
        response = await self.client.put(url, params=params, headers=await self._get_headers())
        response.raise_for_status()
        return response.json()

    async def place_order(self, cart_id: str, security_code: Optional[str] = None) -> Dict[str, Any]:
        user = "anonymous"
        url = f"{self.base_url}/powertools/users/{user}/orders"
        params = {"cartId": cart_id}
        if security_code:
            params["securityCode"] = security_code
        response = await self.client.post(url, params=params, headers=await self._get_headers())
        response.raise_for_status()
        return response.json()
