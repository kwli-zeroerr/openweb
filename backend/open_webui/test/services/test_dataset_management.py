"""Live test for RagFlow Dataset Management APIs.

This test will:
  - List datasets
  - Create a temporary dataset
  - Update its name
  - List again
  - Delete the temporary dataset

Usage:
  python backend/open_webui/test/services/test_dataset_management.py \
    --base http://192.168.2.168:9222

Options:
  --keep  Keep the created dataset (skip delete)
"""
import argparse
import asyncio
import os
import random
import string
import sys
from pathlib import Path

# Ensure backend package is importable
backend_dir = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(backend_dir))

from open_webui.services.ragflow.dataset_management import RagFlowDatasetClient
from open_webui.services.ragflow import (
    DEFAULT_RAGFLOW_BASE_URL,
    DEFAULT_RAGFLOW_API_KEY,
)


def _rand_suffix(n: int = 6) -> str:
    return "".join(random.choices(string.ascii_lowercase + string.digits, k=n))


async def run(base: str, key: str, keep: bool, delete_id: str = "", graph_ds: str = "", delete_graph: bool = False):
    client = RagFlowDatasetClient(base_url=base, api_key=key)

    print("=== List datasets (before) ===")
    try:
        ds_before = await client.list(page=1, page_size=5)
        for i, ds in enumerate(ds_before, 1):
            print(f"  {i}. {ds.get('name')} ({ds.get('id')})")
    except Exception as e:
        print(f"  ❌ list failed: {e}")

    # Optional: knowledge graph checks
    if graph_ds:
        print(f"\n=== Get knowledge graph for {graph_ds} ===")
        try:
            graph = await client.get_knowledge_graph(graph_ds)
            print(f"  ✅ graph nodes: {len(graph.get('graph',{}).get('nodes', []))}")
        except Exception as e:
            print(f"  ❌ get graph failed: {e}")
        if delete_graph:
            print("=== Delete knowledge graph ===")
            try:
                resp = await client.delete_knowledge_graph(graph_ds)
                print(f"  ✅ delete graph resp: {resp.get('code','N/A')}")
            except Exception as e:
                print(f"  ❌ delete graph failed: {e}")

    # Handle direct bulk delete if requested
    if delete_id:
        print(f"\n=== Bulk delete dataset {delete_id} ===")
        try:
            resp = await client.delete_many([delete_id])
            print(f"  ✅ bulk delete resp: {resp.get('code','N/A')}")
        except Exception as e:
            print(f"  ❌ bulk delete failed: {e}")
        return 0

    name = f"openwebui_test_{_rand_suffix()}"
    print(f"\n=== Create dataset: {name} ===")
    try:
        created = await client.create(name=name, description="temp ds from test")
        ds_id = created.get("id") or created.get("dataset_id") or created.get("data", {}).get("id")
        print(f"  ✅ created: id={ds_id}")
    except Exception as e:
        print(f"  ❌ create failed: {e}")
        return 1

    print("\n=== Update dataset name ===")
    try:
        new_name = name + "_upd"
        await client.update(ds_id, name=new_name)
        print(f"  ✅ updated name -> {new_name}")
    except Exception as e:
        print(f"  ❌ update failed: {e}")

    print("\n=== List datasets (after) ===")
    try:
        ds_after = await client.list(page=1, page_size=5)
        for i, ds in enumerate(ds_after, 1):
            print(f"  {i}. {ds.get('name')} ({ds.get('id')})")
    except Exception as e:
        print(f"  ❌ list failed: {e}")

    if not keep:
        print("\n=== Delete dataset ===")
        try:
            # Prefer bulk delete due to possible 405 on path delete
            resp = await client.delete_many([ds_id])
            print(f"  ✅ bulk deleted (code: {resp.get('code','N/A')})")
        except Exception as e:
            print(f"  ❌ delete failed: {e}")

    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser("RagFlow Dataset Management Live Test")
    parser.add_argument("--base", default=os.getenv("RAGFLOW_BASE_URL", DEFAULT_RAGFLOW_BASE_URL))
    parser.add_argument("--key", default=os.getenv("RAGFLOW_API_KEY", DEFAULT_RAGFLOW_API_KEY))
    parser.add_argument("--keep", action="store_true")
    parser.add_argument("--delete-id", default="", help="If provided, bulk delete this dataset id and exit")
    parser.add_argument("--graph-dataset-id", default="", help="Dataset id to get/delete knowledge graph")
    parser.add_argument("--delete-graph", action="store_true", help="Delete knowledge graph after fetching")
    args = parser.parse_args()

    exit(asyncio.run(run(args.base, args.key, args.keep, args.delete_id, args.graph_dataset_id, args.delete_graph)))


