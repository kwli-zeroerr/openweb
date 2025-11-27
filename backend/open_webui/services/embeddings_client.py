import asyncio
import logging
from typing import List, Optional

import aiohttp

logger = logging.getLogger(__name__)


def _get_vllm_url_from_request(request) -> str:
    try:
        cfg = getattr(getattr(request, "app", None), "state", None)
        if cfg and getattr(cfg, "config", None):
            url = getattr(cfg.config, "RAG_VLLM_EMBEDDING_URL", None)
            if isinstance(url, str) and url.strip():
                return url.rstrip("/")
    except Exception:
        pass
    return "http://192.168.1.232:8010"  # safe default


class EmbeddingsClient:
    """Async client for vLLM/OpenAI-compatible embeddings endpoint."""

    def __init__(self, base_url: str, timeout_s: float = 60.0):
        self.base_url = base_url.rstrip("/") + "/v1/embeddings"
        self.timeout = aiohttp.ClientTimeout(total=timeout_s)

    async def embed_one(self, text: str) -> List[float]:
        data = await self.embed_batch([text])
        return data[0]

    async def embed_batch(
        self,
        texts: List[str],
        batch_size: int = 100,
        max_retries: int = 2,
        retry_backoff_s: float = 0.5,
    ) -> List[List[float]]:
        results: List[List[float]] = []
        async with aiohttp.ClientSession() as session:
            for i in range(0, len(texts), batch_size):
                batch = texts[i : i + batch_size]
                attempt = 0
                while True:
                    attempt += 1
                    try:
                        async with session.post(
                            self.base_url,
                            json={"input": batch},
                            timeout=self.timeout,
                        ) as resp:
                            if resp.status != 200:
                                body = await resp.text()
                                raise RuntimeError(f"{resp.status}: {body}")
                            payload = await resp.json()
                            if "data" not in payload:
                                raise RuntimeError("Invalid embeddings response: missing data")
                            for item in payload["data"]:
                                emb = item.get("embedding")
                                if not isinstance(emb, list):
                                    raise RuntimeError("Invalid embedding item type")
                                results.append([float(x) for x in emb])
                            break
                    except Exception as e:
                        if attempt > max_retries:
                            logger.error(f"embed_batch failed at slice {i}: {e}")
                            raise
                        await asyncio.sleep(retry_backoff_s * attempt)
        return results


def get_embeddings_client(request=None) -> EmbeddingsClient:
    base = _get_vllm_url_from_request(request)
    return EmbeddingsClient(base_url=base)


