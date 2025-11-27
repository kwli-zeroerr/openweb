import aiohttp
from typing import Any, Dict, List, Optional, Tuple

from . import get_base_url, get_api_key, get_timeout


class RagFlowFileClient:
    def __init__(self, base_url: str, api_key: Optional[str] = None, timeout_s: float = 60.0):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key or ""
        self.timeout = aiohttp.ClientTimeout(total=timeout_s)

    def _headers(self) -> Dict[str, str]:
        headers = {}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    async def list(
        self,
        dataset_id: str,
        *,
        page: Optional[int] = None,
        page_size: Optional[int] = None,
        orderby: Optional[str] = None,
        desc: Optional[bool] = None,
        keywords: Optional[str] = None,
        document_id: Optional[str] = None,
        name: Optional[str] = None,
        create_time_from: Optional[int] = None,
        create_time_to: Optional[int] = None,
        suffix: Optional[List[str]] = None,
        run: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        url = f"{self.base_url}/api/v1/datasets/{dataset_id}/documents"
        params: Dict[str, Any] = {}
        if page is not None:
            params["page"] = page
        if page_size is not None:
            params["page_size"] = page_size
        if orderby is not None:
            params["orderby"] = orderby
        if desc is not None:
            params["desc"] = str(bool(desc)).lower()
        if keywords is not None:
            params["keywords"] = keywords
        if document_id is not None:
            params["id"] = document_id
        if name is not None:
            params["name"] = name
        if create_time_from is not None:
            params["create_time_from"] = create_time_from
        if create_time_to is not None:
            params["create_time_to"] = create_time_to
        if suffix:
            params["suffix"] = suffix
        if run:
            params["run"] = run

        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=self._headers(), params=params, timeout=self.timeout) as resp:
                resp.raise_for_status()
                payload = await resp.json()

                # Handle different response formats
                if isinstance(payload, dict):
                    # Check for error code
                    if payload.get("code") not in (None, 0):
                        raise RuntimeError(f"RagFlow list documents error: {payload}")

                    # Try data field
                    data = payload.get("data")
                    if isinstance(data, list):
                        return data
                    if isinstance(data, dict):
                        # Common: {data: {docs: [...], total: N}}
                        if "docs" in data and isinstance(data["docs"], list):
                            return data["docs"]
                        # data.documents or data.data
                        if "documents" in data:
                            return data.get("documents") or []
                        if "data" in data and isinstance(data["data"], list):
                            return data["data"]

                    # Check root level
                    if "documents" in payload and isinstance(payload["documents"], list):
                        return payload["documents"]

                # If payload itself is a list
                if isinstance(payload, list):
                    return payload

                # Empty result
                return []

    async def upload(
        self,
        dataset_id: str,
        files: List[Tuple[str, bytes, str]],
    ) -> Dict[str, Any]:
        """Upload one or multiple files.

        Args:
            dataset_id: Dataset to upload into
            files: List of tuples (filename, content_bytes, content_type)
        """
        url = f"{self.base_url}/api/v1/datasets/{dataset_id}/documents"
        form = aiohttp.FormData()
        for filename, content, content_type in files:
            # 确保文件名是UTF-8字符串，避免中文乱码
            # aiohttp.FormData会自动处理UTF-8编码的文件名
            if isinstance(filename, bytes):
                filename = filename.decode('utf-8')
            elif not isinstance(filename, str):
                filename = str(filename)
            
            # 使用quote_chars参数确保特殊字符正确处理（aiohttp 3.8+支持）
            # 对于旧版本，直接传递UTF-8字符串即可
            form.add_field("file", content, filename=filename, content_type=content_type or "application/octet-stream")
        
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=self._headers(), data=form, timeout=self.timeout) as resp:
                resp.raise_for_status()
                payload = await resp.json()
                if isinstance(payload, dict) and payload.get("code", 0) != 0:
                    raise RuntimeError(f"RagFlow upload documents error: {payload}")
                return payload.get("data", payload)

    async def update(
        self,
        dataset_id: str,
        document_id: str,
        *,
        name: Optional[str] = None,
        meta_fields: Optional[Dict[str, Any]] = None,
        chunk_method: Optional[str] = None,
        parser_config: Optional[Dict[str, Any]] = None,
        enabled: Optional[int] = None,
    ) -> Dict[str, Any]:
        url = f"{self.base_url}/api/v1/datasets/{dataset_id}/documents/{document_id}"
        body: Dict[str, Any] = {}
        if name is not None:
            body["name"] = name
        if meta_fields is not None:
            body["meta_fields"] = meta_fields
        if chunk_method is not None:
            body["chunk_method"] = chunk_method
        if parser_config is not None:
            body["parser_config"] = parser_config
        if enabled is not None:
            body["enabled"] = enabled

        headers = {"Content-Type": "application/json; charset=utf-8", **self._headers()}
        async with aiohttp.ClientSession() as session:
            async with session.put(url, headers=headers, json=body, timeout=self.timeout) as resp:
                resp.raise_for_status()
                # aiohttp会自动处理UTF-8编码的JSON响应
                payload = await resp.json()
                if isinstance(payload, dict) and payload.get("code", 0) != 0:
                    raise RuntimeError(f"RagFlow update document error: {payload}")
                return payload

    async def download(self, dataset_id: str, document_id: str) -> bytes:
        url = f"{self.base_url}/api/v1/datasets/{dataset_id}/documents/{document_id}"
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=self._headers(), timeout=self.timeout) as resp:
                resp.raise_for_status()
                return await resp.read()

    async def delete(self, dataset_id: str, ids: Optional[List[str]] = None) -> Dict[str, Any]:
        url = f"{self.base_url}/api/v1/datasets/{dataset_id}/documents"
        body: Dict[str, Any] = {}
        if ids is not None:
            body["ids"] = ids
        headers = {"Content-Type": "application/json", **self._headers()}
        async with aiohttp.ClientSession() as session:
            async with session.delete(url, headers=headers, json=body, timeout=self.timeout) as resp:
                resp.raise_for_status()
                payload = await resp.json()
                if isinstance(payload, dict) and payload.get("code", 0) != 0:
                    raise RuntimeError(f"RagFlow delete documents error: {payload}")
                return payload

    async def parse_documents(self, dataset_id: str, document_ids: List[str]) -> Dict[str, Any]:
        url = f"{self.base_url}/api/v1/datasets/{dataset_id}/chunks"
        body = {"document_ids": document_ids}
        headers = {"Content-Type": "application/json", **self._headers()}
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, json=body, timeout=self.timeout) as resp:
                resp.raise_for_status()
                payload = await resp.json()
                if isinstance(payload, dict) and payload.get("code", 0) != 0:
                    raise RuntimeError(f"RagFlow parse documents error: {payload}")
                return payload

    async def stop_parsing(self, dataset_id: str, document_ids: List[str]) -> Dict[str, Any]:
        url = f"{self.base_url}/api/v1/datasets/{dataset_id}/chunks"
        body = {"document_ids": document_ids}
        headers = {"Content-Type": "application/json", **self._headers()}
        async with aiohttp.ClientSession() as session:
            async with session.delete(url, headers=headers, json=body, timeout=self.timeout) as resp:
                resp.raise_for_status()
                payload = await resp.json()
                if isinstance(payload, dict) and payload.get("code", 0) != 0:
                    raise RuntimeError(f"RagFlow stop parsing error: {payload}")
                return payload


def get_client(request=None) -> RagFlowFileClient:
    return RagFlowFileClient(base_url=get_base_url(request), api_key=get_api_key(request), timeout_s=get_timeout(request))


