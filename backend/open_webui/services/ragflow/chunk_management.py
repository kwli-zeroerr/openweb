import aiohttp
import logging
from typing import Any, Dict, List, Optional, Tuple

from . import get_base_url, get_api_key, get_timeout

logger = logging.getLogger(__name__)


class RagFlowChunkClient:
    def __init__(self, base_url: str, api_key: Optional[str] = None, timeout_s: float = 60.0):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key or ""
        self.timeout = aiohttp.ClientTimeout(total=timeout_s)

    def _headers(self) -> Dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    async def add_chunk(
        self,
        dataset_id: str,
        document_id: str,
        content: str,
        *,
        important_keywords: Optional[List[str]] = None,
        questions: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Add a chunk to a specified document in a dataset.

        Args:
            dataset_id: The dataset ID
            document_id: The document ID
            content: The text content of the chunk (required)
            important_keywords: Key terms or phrases to tag with the chunk
            questions: Questions for embedding-based chunks

        Returns:
            Response data with chunk information including id, create_time, etc.
        """
        url = f"{self.base_url}/api/v1/datasets/{dataset_id}/documents/{document_id}/chunks"
        body: Dict[str, Any] = {"content": content}
        if important_keywords is not None:
            body["important_keywords"] = important_keywords
        if questions is not None:
            body["questions"] = questions

        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=self._headers(), json=body, timeout=self.timeout) as resp:
                resp.raise_for_status()
                payload = await resp.json()
                if isinstance(payload, dict) and payload.get("code", 0) != 0:
                    raise RuntimeError(f"RagFlow add chunk error: {payload}")
                return payload.get("data", payload)

    async def list_chunks(
        self,
        dataset_id: str,
        document_id: str,
        *,
        keywords: Optional[str] = None,
        page: Optional[int] = None,
        page_size: Optional[int] = None,
        chunk_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """List chunks in a specified document.

        Args:
            dataset_id: The dataset ID
            document_id: The document ID
            keywords: Keywords used to match chunk content (filter)
            page: Page number (defaults to 1)
            page_size: Maximum number of chunks per page (defaults to 1024)
            chunk_id: The ID of a specific chunk to retrieve

        Returns:
            Response data with chunks list, doc info, and total count
        """
        url = f"{self.base_url}/api/v1/datasets/{dataset_id}/documents/{document_id}/chunks"
        params: Dict[str, Any] = {}
        if keywords is not None:
            params["keywords"] = keywords
        if page is not None:
            params["page"] = page
        if page_size is not None:
            params["page_size"] = page_size
        if chunk_id is not None:
            params["id"] = chunk_id

        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=self._headers(), params=params, timeout=self.timeout) as resp:
                resp.raise_for_status()
                payload = await resp.json()
                if isinstance(payload, dict) and payload.get("code", 0) != 0:
                    raise RuntimeError(f"RagFlow list chunks error: {payload}")
                return payload.get("data", payload)

    async def delete_chunks(
        self,
        dataset_id: str,
        document_id: str,
        *,
        chunk_ids: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Delete chunks by ID. If chunk_ids is not specified, all chunks of the document will be deleted.

        Args:
            dataset_id: The dataset ID
            document_id: The document ID
            chunk_ids: The IDs of chunks to delete. If None, deletes all chunks in the document.

        Returns:
            Response with code=0 on success
        """
        url = f"{self.base_url}/api/v1/datasets/{dataset_id}/documents/{document_id}/chunks"
        body: Dict[str, Any] = {}
        if chunk_ids is not None:
            body["chunk_ids"] = chunk_ids

        async with aiohttp.ClientSession() as session:
            async with session.delete(url, headers=self._headers(), json=body, timeout=self.timeout) as resp:
                resp.raise_for_status()
                payload = await resp.json()
                if isinstance(payload, dict) and payload.get("code", 0) != 0:
                    raise RuntimeError(f"RagFlow delete chunks error: {payload}")
                return payload

    async def update_chunk(
        self,
        dataset_id: str,
        document_id: str,
        chunk_id: str,
        *,
        content: Optional[str] = None,
        important_keywords: Optional[List[str]] = None,
        available: Optional[bool] = None,
    ) -> Dict[str, Any]:
        """Update content or configurations for a specified chunk.

        Args:
            dataset_id: The dataset ID
            document_id: The document ID
            chunk_id: The ID of the chunk to update
            content: The text content of the chunk
            important_keywords: Key terms or phrases to tag with the chunk
            available: Chunk availability status (true=available, false=unavailable)

        Returns:
            Response with code=0 on success
        """
        url = f"{self.base_url}/api/v1/datasets/{dataset_id}/documents/{document_id}/chunks/{chunk_id}"
        body: Dict[str, Any] = {}
        if content is not None:
            body["content"] = content
        if important_keywords is not None:
            body["important_keywords"] = important_keywords
        if available is not None:
            body["available"] = available

        async with aiohttp.ClientSession() as session:
            async with session.put(url, headers=self._headers(), json=body, timeout=self.timeout) as resp:
                resp.raise_for_status()
                payload = await resp.json()
                if isinstance(payload, dict) and payload.get("code", 0) != 0:
                    raise RuntimeError(f"RagFlow update chunk error: {payload}")
                return payload

    async def retrieve(
        self,
        question: str,
        dataset_ids: List[str],
        *,
        document_ids: Optional[List[str]] = None,
        page: Optional[int] = None,
        page_size: Optional[int] = None,
        similarity_threshold: Optional[float] = None,
        vector_similarity_weight: Optional[float] = None,
        top_k: Optional[int] = None,
        rerank_id: Optional[str] = None,
        keyword: Optional[bool] = None,
        highlight: Optional[bool] = None,
        cross_languages: Optional[List[str]] = None,
        metadata_condition: Optional[Dict[str, Any]] = None,
    ) -> Tuple[List[Dict[str, Any]], List[float]]:
        """Retrieve chunks from specified datasets.

        Args:
            question: The user query or query keywords (required)
            dataset_ids: The IDs of datasets to search (required if document_ids not set)
            document_ids: The IDs of documents to search (required if dataset_ids not set)
            page: Page number (defaults to 1)
            page_size: Maximum chunks per page (defaults to 30)
            similarity_threshold: Minimum similarity score (defaults to 0.2)
            vector_similarity_weight: Weight of vector cosine similarity (defaults to 0.3)
            top_k: Number of chunks for vector cosine computation (defaults to 1024)
            rerank_id: ID of the rerank model
            keyword: Enable keyword-based matching (default: false)
            highlight: Enable highlighting of matched terms (default: false)
            cross_languages: Languages to translate into for cross-language retrieval
            metadata_condition: Metadata filter conditions

        Returns:
            Tuple of (documents list, scores list)
        """
        url = f"{self.base_url}/api/v1/retrieval"
        body: Dict[str, Any] = {
            "question": question,
        }
        if dataset_ids:
            body["dataset_ids"] = dataset_ids
        if document_ids:
            body["document_ids"] = document_ids
        if page is not None:
            body["page"] = page
        if page_size is not None:
            body["page_size"] = page_size
        if similarity_threshold is not None:
            body["similarity_threshold"] = similarity_threshold
        if vector_similarity_weight is not None:
            body["vector_similarity_weight"] = vector_similarity_weight
        if top_k is not None:
            body["top_k"] = top_k
        if rerank_id is not None:
            body["rerank_id"] = rerank_id
        if keyword is not None:
            body["keyword"] = keyword
        if highlight is not None:
            body["highlight"] = highlight
        if cross_languages:
            body["cross_languages"] = cross_languages
        if metadata_condition:
            body["metadata_condition"] = metadata_condition

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, headers=self._headers(), json=body, timeout=self.timeout) as resp:
                    resp.raise_for_status()
                    payload = await resp.json()
                    if payload.get("code") != 0:
                        raise RuntimeError(f"RagFlow API error: {payload.get('message', 'Unknown error')}")

                    chunks = payload.get("data", {}).get("chunks", [])
                    documents = []
                    scores = []
                    for chunk in chunks:
                        documents.append({
                            "content": chunk.get("content", ""),
                            "metadata": {
                                "document_id": chunk.get("document_id"),
                                "document_name": chunk.get("document_keyword"),  # RagFlow uses document_keyword for name
                                "kb_id": chunk.get("kb_id"),
                                "chunk_id": chunk.get("id"),
                                "similarity": chunk.get("similarity"),
                                "vector_similarity": chunk.get("vector_similarity"),
                                "term_similarity": chunk.get("term_similarity"),
                                "highlight": chunk.get("highlight"),
                            }
                        })
                        scores.append(chunk.get("similarity", 0.0))
                    return documents, scores
        except aiohttp.ClientError as e:
            logger.error(f"RagFlow API ClientError: {e}", exc_info=True)
            raise RuntimeError(f"Failed to connect to RagFlow API: {e}")
        except Exception as e:
            logger.error(f"RagFlow API call failed: {e}", exc_info=True)
            raise RuntimeError(f"RagFlow API call failed: {e}")


def get_client(request=None) -> RagFlowChunkClient:
    return RagFlowChunkClient(
        base_url=get_base_url(request),
        api_key=get_api_key(request),
        timeout_s=get_timeout(request)
    )


