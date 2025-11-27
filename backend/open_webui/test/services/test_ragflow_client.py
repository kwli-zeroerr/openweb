import asyncio
import json
import types
import sys
from pathlib import Path as PathType
import os

import pytest

# Ensure backend package is importable
backend_dir = PathType(__file__).parent.parent.parent.parent
sys.path.insert(0, str(backend_dir))

from open_webui.services.ragflow_server import RagFlowClient


class _FakeResp:
    def __init__(self, status: int, payload: dict):
        self.status = status
        self._payload = payload

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def text(self):
        return json.dumps(self._payload)

    async def json(self):
        return self._payload


class _FakeSession:
    def __init__(self, status: int, payload: dict):
        self.status = status
        self.payload = payload

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    def post(self, *args, **kwargs):
        return _FakeResp(self.status, self.payload)


def test_ragflow_client_retrieve_success(monkeypatch):
    payload = {
        "code": 0,
        "data": {
            "chunks": [
                {
                    "content": "ragflow content",
                    "similarity": 0.9,
                    "vector_similarity": 0.88,
                    "term_similarity": 0.92,
                    "document_id": "doc1",
                    "kb_id": "kb1",
                }
            ],
            "doc_aggs": [],
            "total": 1,
        },
    }

    # Patch aiohttp.ClientSession
    import aiohttp

    monkeypatch.setattr(aiohttp, "ClientSession", lambda: _FakeSession(200, payload))

    async def run():
        client = RagFlowClient(base_url="http://fake")
        docs, scores = await client.retrieve("q", ["kb1"], None, 5)
        assert len(docs) == 1
        assert docs[0]["content"] == "ragflow content"
        assert isinstance(scores[0], float) and scores[0] > 0

    asyncio.run(run())


def test_ragflow_client_retrieve_error(monkeypatch):
    bad = {"code": 102, "message": "`datasets` is required."}
    import aiohttp

    monkeypatch.setattr(aiohttp, "ClientSession", lambda: _FakeSession(200, bad))

    async def run():
        client = RagFlowClient(base_url="http://fake")
        with pytest.raises(RuntimeError):
            await client.retrieve("q", [], None, 5)

    asyncio.run(run())



def test_ragflow_client_live_optional():
    """真实调用 RagFlow（仅当设置环境变量时运行）。

    环境变量：
      - RAGFLOW_LIVE_TEST=1 开启
      - RAGFLOW_BASE_URL 可选（默认 http://192.168.2.168）
      - RAGFLOW_API_KEY 可选（默认为提供的 key）
      - RAGFLOW_DATASET_IDS 必填（逗号分隔）
    """
    if os.getenv("RAGFLOW_LIVE_TEST") != "1":
        return  # 跳过

    base = os.getenv("RAGFLOW_BASE_URL", "http://192.168.2.168")
    key = os.getenv("RAGFLOW_API_KEY", "ragflow-Q5MGVmYThhYjU2MjExZjBiNDIzNGEzMj")
    ds_ids = os.getenv("RAGFLOW_DATASET_IDS", "").strip()
    if not ds_ids:
        # 未提供数据集，无法联通测试
        return

    dataset_ids = [s.strip() for s in ds_ids.split(",") if s.strip()]

    async def run():
        client = RagFlowClient(base_url=base, api_key=key)
        docs, scores = await client.retrieve("test", dataset_ids, None, 3)
        # 只要接口连通，code=0，则 docs/scores 长度>=0
        assert isinstance(docs, list)
        assert isinstance(scores, list)

    asyncio.run(run())



if __name__ == "__main__":
    """直接运行本文件，联通测试 RagFlow 服务。

    示例：
      python backend/open_webui/test/services/test_ragflow_client.py \
        --base http://192.168.2.168 \
        --key ragflow-XXXX \
        --datasets b2a...,c3d... \
        --question "测试一下" --top_k 5

    若未传参，将从环境变量读取：
      RAGFLOW_BASE_URL, RAGFLOW_API_KEY, RAGFLOW_DATASET_IDS, RAGFLOW_QUESTION, RAGFLOW_TOP_K
    """
    import argparse

    parser = argparse.ArgumentParser("RagFlow live test")
    parser.add_argument("--base", default=os.getenv("RAGFLOW_BASE_URL", "http://192.168.2.168"))
    parser.add_argument("--key", default=os.getenv("RAGFLOW_API_KEY", "ragflow-Q5MGVmYThhYjU2MjExZjBiNDIzNGEzMj"))
    parser.add_argument("--datasets", default=os.getenv("RAGFLOW_DATASET_IDS", ""))
    parser.add_argument("--question", default=os.getenv("RAGFLOW_QUESTION", "测试一下"))
    parser.add_argument("--top_k", type=int, default=int(os.getenv("RAGFLOW_TOP_K", "5")))
    args = parser.parse_args()

    if not args.datasets.strip():
        print("请提供 --datasets 或设置 RAGFLOW_DATASET_IDS（逗号分隔）")
        sys.exit(1)

    dataset_ids = [s.strip() for s in args.datasets.split(",") if s.strip()]

    async def main():
        client = RagFlowClient(base_url=args.base, api_key=args.key)
        docs, scores = await client.retrieve(args.question, dataset_ids, None, args.top_k)
        print(f"共返回 {len(docs)} 条")
        for i, (d, s) in enumerate(zip(docs, scores), 1):
            print(f"{i}. score={s:.4f}")
            print((d.get("content") or "")[:200].replace("\n", " "))
            print()

    asyncio.run(main())
