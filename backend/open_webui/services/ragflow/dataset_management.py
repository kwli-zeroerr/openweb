import aiohttp
from typing import Any, Dict, List, Optional

from . import get_base_url, get_api_key


class RagFlowDatasetClient:
    def __init__(self, base_url: str, api_key: Optional[str] = None, timeout_s: float = 30.0):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key or ""
        self.timeout = aiohttp.ClientTimeout(total=timeout_s)

    def _headers(self) -> Dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    async def list(
        self,
        *,
        page: Optional[int] = None,
        page_size: Optional[int] = None,
        orderby: Optional[str] = None,
        desc: Optional[bool] = None,
        name: Optional[str] = None,
        dataset_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        url = f"{self.base_url}/api/v1/datasets"
        params: Dict[str, Any] = {}
        if page is not None:
            params["page"] = page
        if page_size is not None:
            params["page_size"] = page_size
        if orderby is not None:
            params["orderby"] = orderby
        if desc is not None:
            params["desc"] = str(bool(desc)).lower()
        if name is not None:
            params["name"] = name
        if dataset_id is not None:
            params["id"] = dataset_id

        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=self._headers(), params=params, timeout=self.timeout) as resp:
                resp.raise_for_status()
                payload = await resp.json()
                # RagFlow returns either {code:0,data:{...}} or {data:[...]}
                if isinstance(payload, dict) and payload.get("code") not in (None, 0):
                    raise RuntimeError(f"RagFlow list datasets error: {payload}")

                data = payload.get("data") if isinstance(payload, dict) else None
                if isinstance(data, list):
                    return data
                if isinstance(data, dict):
                    # Common: {data: {data:[...], total: N}}
                    if "data" in data and isinstance(data["data"], list):
                        return data["data"]
                    if "datasets" in data and isinstance(data["datasets"], list):
                        return data["datasets"]

                if isinstance(payload, list):
                    return payload
                if isinstance(payload, dict) and isinstance(payload.get("datasets"), list):
                    return payload["datasets"]
                return []

    async def create(
        self,
        name: str,
        *,
        avatar: Optional[str] = None,
        description: Optional[str] = None,
        embedding_model: Optional[str] = None,
        permission: Optional[str] = None,
        chunk_method: Optional[str] = None,
        parser_config: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Create dataset following RagFlow API schema.

        Only provided fields are sent in the request body to keep payload minimal.
        """
        url = f"{self.base_url}/api/v1/datasets"
        body: Dict[str, Any] = {"name": name}
        if avatar is not None:
            body["avatar"] = avatar
        if description is not None:
            body["description"] = description
        if embedding_model is not None:
            body["embedding_model"] = embedding_model
        if permission is not None:
            body["permission"] = permission
        if chunk_method is not None:
            body["chunk_method"] = chunk_method
        if parser_config is not None:
            body["parser_config"] = parser_config

        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=self._headers(), json=body, timeout=self.timeout) as resp:
                resp.raise_for_status()
                payload = await resp.json()
                # Normalize RagFlow success format {code:0,data:{...}}
                if isinstance(payload, dict):
                    if payload.get("code", 0) != 0:
                        raise RuntimeError(f"RagFlow create dataset error: {payload}")
                    return payload.get("data", payload)
                return payload

    async def delete(self, dataset_id: str) -> Dict[str, Any]:
        url = f"{self.base_url}/api/v1/datasets/{dataset_id}"
        async with aiohttp.ClientSession() as session:
            async with session.delete(url, headers=self._headers(), timeout=self.timeout) as resp:
                resp.raise_for_status()
                payload = await resp.json()
                if isinstance(payload, dict) and payload.get("code") not in (None, 0):
                    raise RuntimeError(f"RagFlow delete dataset error: {payload}")
                return payload

    async def delete_many(self, ids: Optional[List[str]]) -> Dict[str, Any]:
        """DELETE /api/v1/datasets with ids or null (delete all)."""
        url = f"{self.base_url}/api/v1/datasets"
        headers = {"Content-Type": "application/json", **self._headers()}
        body: Dict[str, Any] = {"ids": ids}  # ids can be None to delete all
        async with aiohttp.ClientSession() as session:
            async with session.delete(url, headers=headers, json=body, timeout=self.timeout) as resp:
                resp.raise_for_status()
                payload = await resp.json()
                if isinstance(payload, dict) and payload.get("code") not in (None, 0):
                    raise RuntimeError(f"RagFlow delete many datasets error: {payload}")
                return payload

    async def update(
        self,
        dataset_id: str,
        *,
        name: Optional[str] = None,
        avatar: Optional[str] = None,
        description: Optional[str] = None,
        embedding_model: Optional[str] = None,
        permission: Optional[str] = None,
        chunk_method: Optional[str] = None,
        pagerank: Optional[int] = None,
        parser_config: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        url = f"{self.base_url}/api/v1/datasets/{dataset_id}"
        body: Dict[str, Any] = {}
        if name is not None:
            body["name"] = name
        if avatar is not None:
            body["avatar"] = avatar
        if description is not None:
            body["description"] = description
        if embedding_model is not None:
            body["embedding_model"] = embedding_model
        if permission is not None:
            body["permission"] = permission
        if chunk_method is not None:
            body["chunk_method"] = chunk_method
        if pagerank is not None:
            body["pagerank"] = pagerank
        if parser_config is not None:
            body["parser_config"] = parser_config

        headers = {"Content-Type": "application/json", **self._headers()}
        async with aiohttp.ClientSession() as session:
            async with session.put(url, headers=headers, json=body, timeout=self.timeout) as resp:
                resp.raise_for_status()
                payload = await resp.json()
                if isinstance(payload, dict) and payload.get("code") not in (None, 0):
                    raise RuntimeError(f"RagFlow update dataset error: {payload}")
                return payload

    async def get_knowledge_graph(self, dataset_id: str) -> Dict[str, Any]:
        url = f"{self.base_url}/api/v1/datasets/{dataset_id}/knowledge_graph"
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=self._headers(), timeout=self.timeout) as resp:
                resp.raise_for_status()
                payload = await resp.json()
                if isinstance(payload, dict) and payload.get("code") not in (None, 0):
                    raise RuntimeError(f"RagFlow get knowledge graph error: {payload}")
                return payload.get("data", payload)

    async def delete_knowledge_graph(self, dataset_id: str) -> Dict[str, Any]:
        url = f"{self.base_url}/api/v1/datasets/{dataset_id}/knowledge_graph"
        async with aiohttp.ClientSession() as session:
            async with session.delete(url, headers=self._headers(), timeout=self.timeout) as resp:
                resp.raise_for_status()
                payload = await resp.json()
                if isinstance(payload, dict) and payload.get("code") not in (None, 0):
                    raise RuntimeError(f"RagFlow delete knowledge graph error: {payload}")
                return payload


def get_client(request=None) -> RagFlowDatasetClient:
    return RagFlowDatasetClient(base_url=get_base_url(request), api_key=get_api_key(request))


