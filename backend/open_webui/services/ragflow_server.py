import logging
from typing import List, Tuple, Dict, Any, Optional

import aiohttp

logger = logging.getLogger(__name__)


def _cfg(request, name: str, default: Optional[str] = None) -> Optional[str]:
    try:
        cfg = getattr(getattr(request, "app", None), "state", None)
        if cfg and getattr(cfg, "config", None):
            val = getattr(cfg.config, name, None)
            if isinstance(val, str) and val.strip():
                return val
    except Exception:
        pass
    return default


class RagFlowClient:
    def __init__(self, base_url: str, api_key: Optional[str] = None, timeout_s: float = 30.0):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key or ""
        self.timeout = aiohttp.ClientTimeout(total=timeout_s)

    async def retrieve(
        self,
        question: str,
        dataset_ids: List[str],
        document_ids: Optional[List[str]] = None,
        top_k: int = 10,
    ) -> Tuple[List[Dict[str, Any]], List[float]]:
        url = f"{self.base_url}/api/v1/retrieval"
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        body: Dict[str, Any] = {
            "question": question,
            "dataset_ids": dataset_ids,
            "top_k": top_k,
            # 使用 RagFlow 默认，其余参数不传以降低耦合
        }
        if document_ids:
            body["document_ids"] = document_ids

        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, json=body, timeout=self.timeout) as resp:
                if resp.status != 200:
                    txt = await resp.text()
                    raise RuntimeError(f"RagFlow {resp.status}: {txt}")
                payload = await resp.json()
                if payload.get("code") != 0 or "data" not in payload:
                    raise RuntimeError(f"RagFlow error: {payload}")
                data = payload["data"] or {}
                chunks = data.get("chunks", [])

                documents: List[Dict[str, Any]] = []
                scores: List[float] = []
                for c in chunks:
                    documents.append(
                        {
                            "content": c.get("content", ""),
                            "metadata": {
                                k: c.get(k)
                                for k in (
                                    "similarity",
                                    "vector_similarity",
                                    "term_similarity",
                                    "document_id",
                                    "kb_id",
                                    "positions",
                                )
                            },
                        }
                    )
                    try:
                        scores.append(float(c.get("similarity", 0.0)))
                    except Exception:
                        scores.append(0.0)

                return documents, scores


def get_ragflow_client(request) -> RagFlowClient:
    base = _cfg(request, "RAGFLOW_BASE_URL", "http://192.168.2.168")
    key = _cfg(request, "RAGFLOW_API_KEY", "ragflow-Q5MGVmYThhYjU2MjExZjBiNDIzNGEzMj")
    return RagFlowClient(base_url=base, api_key=key)


