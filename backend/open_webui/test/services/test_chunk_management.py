"""Test script for RagFlow chunk management APIs.

This script can be run directly to test chunk management operations:
  python backend/open_webui/test/services/test_chunk_management.py \
    --base http://192.168.2.168 \
    --key ragflow-XXXX \
    --dataset-id <dataset_id> \
    --document-id <document_id> \
    --action <add|list|update|delete|retrieve>

All parameters can also be provided via environment variables:
  RAGFLOW_BASE_URL, RAGFLOW_API_KEY, RAGFLOW_DATASET_ID, RAGFLOW_DOCUMENT_ID
"""
import asyncio
import argparse
import os
import sys
from pathlib import Path

# Ensure backend package is importable
backend_dir = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(backend_dir))

from open_webui.services.ragflow.chunk_management import RagFlowChunkClient
from open_webui.services.ragflow.dataset_management import RagFlowDatasetClient
from open_webui.services.ragflow.file_management import RagFlowFileClient
from open_webui.services.ragflow import DEFAULT_RAGFLOW_BASE_URL, DEFAULT_RAGFLOW_API_KEY


async def test_upload_file(client: RagFlowFileClient, dataset_id: str, filename: str = "test_chunk_api.txt", content: bytes = b"Hello RagFlow from API test", content_type: str = "text/plain"):
    """Test uploading a single text file."""
    print(f"\n--- Testing upload document ---")
    print(f"Dataset ID: {dataset_id}")
    print(f"Filename: {filename}")

    try:
        data = await client.upload(dataset_id, files=[(filename, content, content_type)])
        docs = data if isinstance(data, list) else data.get("data") or data
        created = docs[0] if isinstance(docs, list) and docs else {}
        doc_id = created.get("id") or created.get("document_id")
        print(f"✅ Uploaded. Document ID: {doc_id}")
        return doc_id
    except Exception as e:
        print(f"❌ Failed: {e}")
        return None


async def test_parse_documents(client: RagFlowFileClient, dataset_id: str, document_ids: list):
    """Test triggering parse for uploaded documents."""
    print(f"\n--- Testing parse documents ---")
    print(f"Dataset ID: {dataset_id}")
    print(f"Document IDs: {document_ids}")

    try:
        resp = await client.parse_documents(dataset_id, document_ids)
        print(f"✅ Parse triggered (code: {resp.get('code', 'N/A')})")
        return True
    except Exception as e:
        print(f"❌ Failed: {e}")
        return False


async def list_datasets(client: RagFlowDatasetClient):
    """List all available datasets."""
    print("\n--- Available Datasets (Knowledge Bases) ---")
    try:
        datasets = await client.list()
        if not datasets:
            print("  ⚠️  No datasets found")
            return []
        
        print(f"  Found {len(datasets)} dataset(s):\n")
        for i, ds in enumerate(datasets, 1):
            ds_id = ds.get("id", "N/A")
            ds_name = ds.get("name", "Unnamed")
            doc_count = ds.get("document_count", 0)
            chunk_count = ds.get("chunk_count", 0)
            print(f"  {i}. {ds_name}")
            print(f"     ID: {ds_id}")
            print(f"     Documents: {doc_count}, Chunks: {chunk_count}")
            if ds.get("description"):
                print(f"     Description: {ds['description'][:80]}...")
            print()
        return datasets
    except Exception as e:
        print(f"  ❌ Failed to list datasets: {e}")
        return []


async def list_documents(client: RagFlowFileClient, dataset_id: str):
    """List all documents in a dataset."""
    print(f"\n--- Documents in Dataset {dataset_id[:16]}... ---")
    try:
        documents = await client.list(dataset_id)
        if not documents:
            print("  ⚠️  No documents found")
            return []
        
        print(f"  Found {len(documents)} document(s):\n")
        for i, doc in enumerate(documents, 1):
            doc_id = doc.get("id", "N/A")
            doc_name = doc.get("name", "Unnamed")
            doc_status = doc.get("status", "unknown")
            chunk_count = doc.get("chunk_count", 0)
            print(f"  {i}. {doc_name}")
            print(f"     ID: {doc_id}")
            print(f"     Status: {doc_status}, Chunks: {chunk_count}")
            print()
        return documents
    except Exception as e:
        print(f"  ❌ Failed to list documents: {e}")
        return []


async def test_add_chunk(client: RagFlowChunkClient, dataset_id: str, document_id: str, content: str):
    """Test adding a chunk."""
    print(f"\n--- Testing add_chunk ---")
    print(f"Dataset ID: {dataset_id}")
    print(f"Document ID: {document_id}")
    print(f"Content: {content[:100]}...")
    
    try:
        result = await client.add_chunk(
            dataset_id=dataset_id,
            document_id=document_id,
            content=content,
            important_keywords=["test", "chunk"],
            questions=["What is this about?"]
        )
        print(f"✅ Success! Chunk created:")
        print(f"  Chunk ID: {result.get('chunk', {}).get('id', 'N/A')}")
        print(f"  Create time: {result.get('chunk', {}).get('create_time', 'N/A')}")
        return result.get('chunk', {}).get('id')
    except Exception as e:
        print(f"❌ Failed: {e}")
        return None


async def test_list_chunks(client: RagFlowChunkClient, dataset_id: str, document_id: str):
    """Test listing chunks."""
    print(f"\n--- Testing list_chunks ---")
    print(f"Dataset ID: {dataset_id}")
    print(f"Document ID: {document_id}")
    
    try:
        result = await client.list_chunks(
            dataset_id=dataset_id,
            document_id=document_id,
            page=1,
            page_size=10
        )
        chunks = result.get("chunks", [])
        total = result.get("total", 0)
        print(f"✅ Success! Found {total} chunks (showing {len(chunks)}):")
        for i, chunk in enumerate(chunks[:5], 1):  # Show first 5
            print(f"  {i}. ID: {chunk.get('id', 'N/A')}")
            print(f"     Content: {chunk.get('content', '')[:80]}...")
        if len(chunks) > 5:
            print(f"  ... and {len(chunks) - 5} more")
        return chunks[0].get('id') if chunks else None
    except Exception as e:
        print(f"❌ Failed: {e}")
        return None


async def test_update_chunk(
    client: RagFlowChunkClient,
    dataset_id: str,
    document_id: str,
    chunk_id: str,
    new_content: str
):
    """Test updating a chunk."""
    print(f"\n--- Testing update_chunk ---")
    print(f"Dataset ID: {dataset_id}")
    print(f"Document ID: {document_id}")
    print(f"Chunk ID: {chunk_id}")
    print(f"New content: {new_content[:100]}...")
    
    try:
        result = await client.update_chunk(
            dataset_id=dataset_id,
            document_id=document_id,
            chunk_id=chunk_id,
            content=new_content,
            important_keywords=["updated", "test"],
            available=True
        )
        print(f"✅ Success! Chunk updated (code: {result.get('code', 'N/A')})")
        return True
    except Exception as e:
        print(f"❌ Failed: {e}")
        return False


async def test_delete_chunks(
    client: RagFlowChunkClient,
    dataset_id: str,
    document_id: str,
    chunk_ids: list = None
):
    """Test deleting chunks."""
    print(f"\n--- Testing delete_chunks ---")
    print(f"Dataset ID: {dataset_id}")
    print(f"Document ID: {document_id}")
    if chunk_ids:
        print(f"Chunk IDs to delete: {chunk_ids}")
    else:
        print(f"⚠️  Will delete ALL chunks in the document!")
    
    confirm = input("Continue? (yes/no): ").strip().lower()
    if confirm != "yes":
        print("❌ Cancelled by user")
        return False
    
    try:
        result = await client.delete_chunks(
            dataset_id=dataset_id,
            document_id=document_id,
            chunk_ids=chunk_ids
        )
        print(f"✅ Success! Chunks deleted (code: {result.get('code', 'N/A')})")
        return True
    except Exception as e:
        print(f"❌ Failed: {e}")
        return False


async def test_retrieve(
    client: RagFlowChunkClient,
    dataset_ids: list,
    question: str,
    document_ids: list = None
):
    """Test retrieving chunks."""
    print(f"\n--- Testing retrieve ---")
    print(f"Question: {question}")
    print(f"Dataset IDs: {dataset_ids}")
    if document_ids:
        print(f"Document IDs: {document_ids}")
    
    try:
        documents, scores = await client.retrieve(
            question=question,
            dataset_ids=dataset_ids,
            document_ids=document_ids,
            top_k=5,
            highlight=True
        )
        print(f"✅ Success! Found {len(documents)} chunks:")
        for i, (doc, score) in enumerate(zip(documents[:5], scores[:5]), 1):
            print(f"  {i}. Score: {score:.4f}")
            content = doc.get("content", "")
            print(f"     Content: {content[:100]}...")
            metadata = doc.get("metadata", {})
            if metadata.get("highlight"):
                print(f"     Highlight: {metadata['highlight'][:80]}...")
        return True
    except Exception as e:
        print(f"❌ Failed: {e}")
        return False


async def main():
    parser = argparse.ArgumentParser(description="Test RagFlow chunk management APIs")
    parser.add_argument(
        "--base",
        type=str,
        default=os.environ.get("RAGFLOW_BASE_URL", DEFAULT_RAGFLOW_BASE_URL),
        help="RagFlow base URL"
    )
    parser.add_argument(
        "--key",
        type=str,
        default=os.environ.get("RAGFLOW_API_KEY", DEFAULT_RAGFLOW_API_KEY),
        help="RagFlow API Key"
    )
    parser.add_argument(
        "--dataset-id",
        type=str,
        default=os.environ.get("RAGFLOW_DATASET_ID", ""),
        help="Dataset ID"
    )
    parser.add_argument(
        "--document-id",
        type=str,
        default=os.environ.get("RAGFLOW_DOCUMENT_ID", ""),
        help="Document ID"
    )
    parser.add_argument(
        "--action",
        type=str,
        choices=["add", "list", "update", "delete", "retrieve", "upload", "parse", "all"],
        default="all",
        help="Action to test (default: all)"
    )
    parser.add_argument(
        "--chunk-id",
        type=str,
        default="",
        help="Chunk ID (for update/delete operations)"
    )
    parser.add_argument(
        "--content",
        type=str,
        default="This is a test chunk content for RagFlow API testing.",
        help="Content for add/update operations"
    )
    parser.add_argument(
        "--question",
        type=str,
        default="What is this about?",
        help="Question for retrieve operation"
    )
    parser.add_argument(
        "--datasets",
        type=str,
        default=os.environ.get("RAGFLOW_DATASET_IDS", ""),
        help="Comma-separated dataset IDs for retrieve (optional)"
    )
    parser.add_argument(
        "--list-only",
        action="store_true",
        help="Only list available datasets and documents, then exit"
    )
    parser.add_argument(
        "--auto-select",
        action="store_true",
        help="Automatically select the first available dataset/document if not provided"
    )
    
    args = parser.parse_args()
    
    # Skip parameter checks for list-only action
    if not args.list_only:
        # Check required parameters based on action
        if args.action != "retrieve":
            if not args.dataset_id and not args.auto_select:
                print("❌ Error: --dataset-id is required for this action (or use --auto-select)")
                sys.exit(1)
            
            if args.action in ["add", "list", "update", "delete"]:
                if not args.document_id and not args.auto_select:
                    print("❌ Error: --document-id is required for this action (or use --auto-select)")
                    sys.exit(1)
        
        if args.action == "retrieve" and not args.dataset_id and not args.datasets and not args.auto_select:
            print("❌ Error: --dataset-id or --datasets is required for retrieve action (or use --auto-select)")
            sys.exit(1)
        
        if args.action == "update" and not args.chunk_id:
            # chunk_id will be obtained from list_chunks if doing "all"
            pass
    
    # Initialize clients
    chunk_client = RagFlowChunkClient(base_url=args.base, api_key=args.key)
    dataset_client = RagFlowDatasetClient(base_url=args.base, api_key=args.key)
    file_client = RagFlowFileClient(base_url=args.base, api_key=args.key)
    
    print(f"=== RagFlow Chunk Management API Test ===")
    print(f"Base URL: {args.base}")
    print(f"API Key: {'*' * len(args.key) if args.key else 'None'}")
    
    # List available datasets
    datasets = await list_datasets(dataset_client)
    
    if args.list_only:
        if datasets and args.dataset_id:
            await list_documents(file_client, args.dataset_id)
        print("\n✅ Listing complete. Use --dataset-id and --document-id with real IDs to test.")
        sys.exit(0)
    
    # Auto-select or validate dataset_id
    if not args.dataset_id and args.auto_select:
        if datasets:
            args.dataset_id = datasets[0].get("id")
            print(f"\n✅ Auto-selected dataset: {datasets[0].get('name')} ({args.dataset_id})")
        else:
            print("\n❌ No datasets available for auto-selection")
            sys.exit(1)
    
    # List documents if dataset_id is provided
    documents = []
    if args.dataset_id:
        documents = await list_documents(file_client, args.dataset_id)
        
        # Auto-select document if not provided
        if not args.document_id and args.auto_select and documents:
            args.document_id = documents[0].get("id")
            print(f"\n✅ Auto-selected document: {documents[0].get('name')} ({args.document_id})")
    
    print(f"\nAction: {args.action}")
    
    success_count = 0
    total_tests = 0
    
    if args.action in ["upload", "all"]:
        total_tests += 1
        new_doc_id = await test_upload_file(file_client, args.dataset_id)
        if new_doc_id:
            success_count += 1
            if args.action == "all" and not args.document_id:
                args.document_id = new_doc_id

    if args.action in ["add", "all"]:
        total_tests += 1
        chunk_id = await test_add_chunk(chunk_client, args.dataset_id, args.document_id, args.content)
        if chunk_id:
            success_count += 1
            # Store chunk_id for update test
            if args.action == "all" and not args.chunk_id:
                args.chunk_id = chunk_id
    
    if args.action in ["list", "all"]:
        total_tests += 1
        chunk_id = await test_list_chunks(chunk_client, args.dataset_id, args.document_id)
        if chunk_id:
            success_count += 1
            # Use first chunk for update test if no chunk_id provided
            if args.action == "all" and not args.chunk_id:
                args.chunk_id = chunk_id
    
    if args.action in ["update", "all"]:
        if args.chunk_id:
            total_tests += 1
            if await test_update_chunk(
                chunk_client,
                args.dataset_id,
                args.document_id,
                args.chunk_id,
                f"Updated: {args.content}"
            ):
                success_count += 1
        else:
            print("\n⚠️  Skipping update test (no chunk_id available)")
    
    if args.action in ["retrieve", "all"]:
        total_tests += 1
        dataset_ids = []
        
        # Auto-select first dataset if enabled and no dataset_id provided
        if args.auto_select and not args.dataset_id and datasets:
            dataset_ids = [datasets[0].get("id")]
            print(f"\n✅ Auto-selected dataset for retrieve: {datasets[0].get('name')} ({dataset_ids[0]})")
        elif args.dataset_id:
            dataset_ids = [args.dataset_id]
        elif args.datasets:
            # Use provided datasets if they look real (not test values)
            provided_ids = [d.strip() for d in args.datasets.split(",") if d.strip()]
            if provided_ids and not any("dataset_id" in d or "test" in d.lower() for d in provided_ids):
                dataset_ids = provided_ids
            elif provided_ids:
                print(f"\n⚠️  Ignoring test dataset IDs: {provided_ids}")
        
        if dataset_ids:
            if await test_retrieve(chunk_client, dataset_ids, args.question, [args.document_id] if args.document_id else None):
                success_count += 1
        else:
            print("\n⚠️  Skipping retrieve test (no valid dataset_ids available)")
            if datasets:
                print(f"   💡 Available datasets: {[ds.get('id') for ds in datasets[:3]]}")
    
    if args.action in ["parse", "all"]:
        if args.document_id:
            total_tests += 1
            if await test_parse_documents(file_client, args.dataset_id, [args.document_id]):
                success_count += 1
        else:
            print("\n⚠️  Skipping parse test (no document_id available)")

    if args.action in ["delete", "all"]:
        total_tests += 1
        chunk_ids = [args.chunk_id] if args.chunk_id else None
        if await test_delete_chunks(chunk_client, args.dataset_id, args.document_id, chunk_ids):
            success_count += 1
    
    print(f"\n=== Test Summary ===")
    print(f"Total tests: {total_tests}")
    print(f"Successful: {success_count}")
    print(f"Failed: {total_tests - success_count}")
    
    if success_count == total_tests:
        print("✅ All tests passed!")
        sys.exit(0)
    else:
        print("❌ Some tests failed")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())

