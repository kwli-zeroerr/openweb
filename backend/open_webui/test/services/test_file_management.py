"""Standalone live test for RagFlow File Management APIs.

Usage examples:

  # List datasets and documents
  python backend/open_webui/test/services/test_file_management.py \
    --base http://192.168.2.168:9222 \
    --key ragflow-XXXX \
    --action list --auto-select

  # Upload a small text file and trigger parsing
  python backend/open_webui/test/services/test_file_management.py \
    --base http://192.168.2.168:9222 \
    --key ragflow-XXXX \
    --action upload --auto-select

  # Download a document
  python backend/open_webui/test/services/test_file_management.py \
    --base http://192.168.2.168:9222 \
    --key ragflow-XXXX \
    --action download --dataset-id <ds> --document-id <doc> --output /tmp/out.bin

"""
import argparse
import asyncio
import os
import sys
from pathlib import Path

# Ensure backend package is importable
backend_dir = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(backend_dir))

from open_webui.services.ragflow.dataset_management import RagFlowDatasetClient
from open_webui.services.ragflow.file_management import RagFlowFileClient
from open_webui.services.ragflow import (
    DEFAULT_RAGFLOW_BASE_URL,
    DEFAULT_RAGFLOW_API_KEY,
)


async def list_datasets(ds_client: RagFlowDatasetClient):
    print("\n--- Datasets ---")
    try:
        datasets = await ds_client.list()
        if not datasets:
            print("  (empty)")
            return []
        for i, ds in enumerate(datasets, 1):
            print(f"  {i}. {ds.get('name','Unnamed')} ({ds.get('id')}) docs={ds.get('document_count')} chunks={ds.get('chunk_count')}")
        return datasets
    except Exception as e:
        print(f"  ❌ list datasets failed: {e}")
        return []


async def list_documents(file_client: RagFlowFileClient, dataset_id: str):
    print(f"\n--- Documents in {dataset_id} ---")
    try:
        docs = await file_client.list(dataset_id, page=1, page_size=20)
        if not docs:
            print("  (empty)")
            return []
        for i, d in enumerate(docs, 1):
            print(f"  {i}. {d.get('name','Unnamed')} ({d.get('id')}) status={d.get('status')} chunks={d.get('chunk_count',0)}")
        return docs
    except Exception as e:
        print(f"  ❌ list documents failed: {e}")
        return []


async def do_upload(file_client: RagFlowFileClient, dataset_id: str):
    print("\n--- Upload ---")
    try:
        filename = "test_file_mgmt.txt"
        content = b"Hello from test_file_management"
        data = await file_client.upload(dataset_id, [(filename, content, "text/plain")])
        docs = data if isinstance(data, list) else data.get("data") or data
        created = docs[0] if isinstance(docs, list) and docs else {}
        doc_id = created.get("id") or created.get("document_id")
        print(f"  ✅ uploaded: {filename} -> id={doc_id}")
        return doc_id
    except Exception as e:
        print(f"  ❌ upload failed: {e}")
        return None


async def do_update(file_client: RagFlowFileClient, dataset_id: str, document_id: str):
    print("\n--- Update ---")
    try:
        resp = await file_client.update(
            dataset_id,
            document_id,
            name="manual.txt",
            chunk_method="manual",
            parser_config={"chunk_token_num": 128},
        )
        print(f"  ✅ update resp: {resp.get('code','N/A')}")
        return True
    except Exception as e:
        print(f"  ❌ update failed: {e}")
        return False


async def do_download(file_client: RagFlowFileClient, dataset_id: str, document_id: str, output: Path):
    print("\n--- Download ---")
    try:
        content = await file_client.download(dataset_id, document_id)
        output.write_bytes(content)
        print(f"  ✅ saved to {output} ({len(content)} bytes)")
        return True
    except Exception as e:
        print(f"  ❌ download failed: {e}")
        return False


async def do_delete(file_client: RagFlowFileClient, dataset_id: str, ids):
    print("\n--- Delete ---")
    try:
        resp = await file_client.delete(dataset_id, ids=ids)
        print(f"  ✅ delete resp: {resp.get('code','N/A')}")
        return True
    except Exception as e:
        print(f"  ❌ delete failed: {e}")
        return False


async def do_parse(file_client: RagFlowFileClient, dataset_id: str, document_ids):
    print("\n--- Parse ---")
    try:
        resp = await file_client.parse_documents(dataset_id, document_ids)
        print(f"  ✅ parse resp: {resp.get('code','N/A')}")
        return True
    except Exception as e:
        print(f"  ❌ parse failed: {e}")
        return False


async def do_stop(file_client: RagFlowFileClient, dataset_id: str, document_ids):
    print("\n--- Stop Parse ---")
    try:
        resp = await file_client.stop_parsing(dataset_id, document_ids)
        print(f"  ✅ stop resp: {resp.get('code','N/A')}")
        return True
    except Exception as e:
        print(f"  ❌ stop failed: {e}")
        return False


async def main():
    parser = argparse.ArgumentParser("RagFlow File Management Live Test")
    parser.add_argument("--base", default=os.getenv("RAGFLOW_BASE_URL", DEFAULT_RAGFLOW_BASE_URL))
    parser.add_argument("--key", default=os.getenv("RAGFLOW_API_KEY", DEFAULT_RAGFLOW_API_KEY))
    parser.add_argument("--action", choices=["list", "upload", "update", "download", "delete", "parse", "stop", "all"], default="list")
    parser.add_argument("--dataset-id", default=os.getenv("RAGFLOW_DATASET_ID", ""))
    parser.add_argument("--document-id", default=os.getenv("RAGFLOW_DOCUMENT_ID", ""))
    parser.add_argument("--output", default="/tmp/ragflow_download.bin")
    parser.add_argument("--auto-select", action="store_true")
    args = parser.parse_args()

    ds_client = RagFlowDatasetClient(base_url=args.base, api_key=args.key)
    file_client = RagFlowFileClient(base_url=args.base, api_key=args.key)

    print("=== RagFlow File Management Test ===")
    print(f"Base: {args.base}")

    datasets = await list_datasets(ds_client)

    # auto pick dataset
    if not args.dataset_id and args.auto_select and datasets:
        args.dataset_id = datasets[0].get("id")
        print(f"\n✅ Auto-selected dataset: {datasets[0].get('name')} ({args.dataset_id})")

    docs = []
    if args.dataset_id:
        docs = await list_documents(file_client, args.dataset_id)
        if not args.document_id and args.auto_select and docs:
            args.document_id = docs[0].get("id")
            print(f"\n✅ Auto-selected document: {docs[0].get('name')} ({args.document_id})")

    # Execute action(s)
    if args.action in ("upload", "all"):
        new_id = await do_upload(file_client, args.dataset_id)
        if new_id and not args.document_id:
            args.document_id = new_id

    if args.action in ("update", "all") and args.document_id:
        await do_update(file_client, args.dataset_id, args.document_id)

    if args.action in ("download", "all") and args.document_id:
        await do_download(file_client, args.dataset_id, args.document_id, Path(args.output))

    if args.action in ("parse", "all") and args.document_id:
        await do_parse(file_client, args.dataset_id, [args.document_id])

    if args.action in ("stop", "all") and args.document_id:
        await do_stop(file_client, args.dataset_id, [args.document_id])

    if args.action == "delete" and args.document_id:
        await do_delete(file_client, args.dataset_id, [args.document_id])


if __name__ == "__main__":
    asyncio.run(main())



