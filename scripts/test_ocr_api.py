#!/usr/bin/env python3

"""
Simple diagnostic tool for the DeepSeek OCR HTTP API.

Usage:
    python scripts/test_ocr_api.py \
        --base-url http://192.168.195.125:8002 \
        --file /path/to/sample.pdf
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Optional, Tuple

import requests


def log_section(title: str) -> None:
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80)


def check_server_health(base_url: str) -> bool:
    """Check if OCR server is accessible"""
    log_section("Check Server Health")
    try:
        # Try to access docs or root endpoint
        endpoints = ["/docs", "/", "/api/history"]
        for endpoint in endpoints:
            try:
                resp = requests.get(f"{base_url}{endpoint}", timeout=5)
                if resp.status_code in (200, 404, 405):  # 404/405 means server is up
                    print(f"  ✅ Server is accessible at {base_url}")
                    return True
            except:
                continue
        print(f"  ⚠️  Could not verify server health, but continuing...")
        return True  # Continue anyway
    except Exception as exc:
        print(f"  ❌ Server health check failed: {exc}")
        return False


def check_file_access(file_path: Path) -> bool:
    """Check if file exists and is readable"""
    log_section("Check File Access")
    if not file_path.exists():
        print(f"  ❌ File does not exist: {file_path}")
        return False
    
    if not file_path.is_file():
        print(f"  ❌ Path is not a file: {file_path}")
        return False
    
    try:
        size = file_path.stat().st_size
        print(f"  ✅ File exists: {file_path}")
        print(f"  📊 File size: {size:,} bytes ({size / 1024:.2f} KB)")
        
        # Try to read first few bytes
        with file_path.open("rb") as f:
            header = f.read(4)
            if header.startswith(b"%PDF"):
                print(f"  ✅ Valid PDF file (PDF header detected)")
            else:
                print(f"  ⚠️  File may not be a valid PDF (header: {header.hex()})")
        
        return True
    except Exception as exc:
        print(f"  ❌ Cannot access file: {exc}")
        return False


def check_ocr_logs(log_dir: Optional[str] = None) -> None:
    """Try to find and display recent OCR service logs"""
    log_section("Check OCR Service Logs")
    
    # Common log locations
    possible_log_dirs = [
        log_dir,
        "/home/zeroerr-ai72/deepseek-ocr-web/logs",
        "/home/zeroerr-ai72/deepseek-ocr-web/workspace/logs",
        "./logs",
        "./workspace/logs",
    ]
    
    for log_path in possible_log_dirs:
        if not log_path:
            continue
        log_dir_path = Path(log_path)
        if log_dir_path.exists() and log_dir_path.is_dir():
            print(f"  📁 Found log directory: {log_dir_path}")
            # Try to find recent log files
            log_files = sorted(log_dir_path.glob("*.log"), key=lambda p: p.stat().st_mtime, reverse=True)
            if log_files:
                latest_log = log_files[0]
                print(f"  📄 Latest log: {latest_log}")
                try:
                    # Show last 20 lines
                    with latest_log.open("r", encoding="utf-8", errors="ignore") as f:
                        lines = f.readlines()
                        if lines:
                            print(f"  📋 Last 20 lines of log:")
                            for line in lines[-20:]:
                                print(f"      {line.rstrip()}")
                except Exception as e:
                    print(f"  ⚠️  Could not read log: {e}")
                return
    
    print("  ⚠️  Could not find OCR service logs (this is normal if logs are elsewhere)")


def upload_file(base_url: str, file_path: Path) -> Optional[str]:
    log_section("Upload File (/api/upload)")
    if not file_path.exists():
        print(f"  ❌ File does not exist: {file_path}")
        return None

    try:
        with file_path.open("rb") as f:
            files = {"file": (file_path.name, f, "application/octet-stream")}
            resp = requests.post(f"{base_url}/api/upload", files=files, timeout=60)

        if resp.status_code != 200:
            print(f"  ❌ Upload failed: HTTP {resp.status_code}")
            print(f"  ↳ {resp.text}")
            return None

        data = resp.json()
        print(f"  ✅ Upload succeeded: {json.dumps(data, ensure_ascii=False)}")
        return data.get("file_path")
    except Exception as exc:
        print(f"  ❌ Upload exception: {exc}")
        return None


def start_task(
    base_url: str,
    file_path: str,
    prompt: str,
    vlm_prompt: str,
    use_qwen_vlm: bool,
    original_filename: str,
    output_dir: Optional[str] = None,
) -> Optional[str]:
    log_section("Start OCR Task (/api/start)")

    payload = {
        "file_path": file_path,
        "prompt": prompt,
        "vlm_prompt": vlm_prompt,
        "use_qwen_vlm": use_qwen_vlm,
        "original_filename": original_filename,
    }

    if output_dir:
        payload["output_dir"] = output_dir

    print("  ↳ Payload:", json.dumps({k: v for k, v in payload.items() if k != "prompt"}, ensure_ascii=False))

    try:
        resp = requests.post(f"{base_url}/api/start", json=payload, timeout=60)
        resp.raise_for_status()
        data = resp.json()
        print(f"  ✅ Task accepted: {json.dumps(data, ensure_ascii=False)}")
        return data.get("task_id")
    except Exception as exc:
        print(f"  ❌ Failed to start task: {exc}")
        return None


def wait_for_completion(
    base_url: str,
    task_id: str,
    interval: int,
    timeout: int,
    verbose: bool = False,
) -> Tuple[bool, Optional[dict]]:
    log_section(f"Poll Task Progress (/api/progress/{task_id})")
    start_time = time.time()
    last_progress = None
    last_status = None
    error_count = 0

    while time.time() - start_time < timeout:
        try:
            resp = requests.get(f"{base_url}/api/progress/{task_id}", timeout=30)
            resp.raise_for_status()
            data = resp.json()
            state = data.get("state", {})
            progress = state.get("progress", 0)
            status = state.get("status", "unknown")
            message = state.get("message", "")
            result_dir = state.get("result_dir", "")
            total_pages = state.get("total_pages", 0)
            processed_pages = state.get("processed_pages", 0)

            # Print progress if it changed
            if progress != last_progress or status != last_status:
                print(f"  📊 progress={progress}% status={status} pages={processed_pages}/{total_pages}")
                if message:
                    print(f"      message: {message}")
                if result_dir:
                    print(f"      result_dir: {result_dir}")
                last_progress = progress
                last_status = status

            if verbose:
                print(f"  🔍 Full state: {json.dumps(state, indent=4, ensure_ascii=False)}")

            if status == "completed":
                print("  ✅ Task completed.")
                result = requests.get(f"{base_url}/api/result/{task_id}", timeout=30)
                result.raise_for_status()
                return True, result.json()

            if status == "error":
                print(f"  ❌ Task failed!")
                print(f"  📋 Error details:")
                print(f"      message: {message}")
                print(f"      result_dir: {result_dir}")
                print(f"      total_pages: {total_pages}")
                print(f"      processed_pages: {processed_pages}")
                print(f"  📋 Full error response:")
                print(json.dumps(data, indent=2, ensure_ascii=False))
                
                # Try to get more details from latest_result if available
                latest_result = state.get("latest_result", {})
                if latest_result:
                    print(f"  📋 Latest result details:")
                    print(json.dumps(latest_result, indent=2, ensure_ascii=False))
                
                return False, data

        except requests.exceptions.RequestException as exc:
            error_count += 1
            if error_count > 3:
                print(f"  ❌ Too many polling errors, giving up: {exc}")
                return False, None
            print(f"  ⚠️  Polling error ({error_count}/3): {exc}")
        except Exception as exc:
            print(f"  ⚠️  Unexpected error: {exc}")

        time.sleep(interval)

    print(f"  ⏰ Timed out after {timeout} seconds.")
    return False, None


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Test the DeepSeek OCR API.")
    parser.add_argument("--base-url", default="http://127.0.0.1:8002", help="OCR API base URL")
    parser.add_argument("--file", required=True, help="Path to PDF/image to upload")
    parser.add_argument("--output-dir", help="Optional override for OCR output directory")
    parser.add_argument("--interval", type=int, default=3, help="Polling interval in seconds")
    parser.add_argument("--timeout", type=int, default=600, help="Max wait time in seconds")
    parser.add_argument("--prompt", default="<image>\n<|grounding|>Convert to markdown.")
    parser.add_argument("--vlm-prompt", default="请根据 OCR 结果生成高质量 Markdown。")
    parser.add_argument("--no-qwen-vlm", action="store_true", help="Disable Qwen VLM refinement")
    parser.add_argument("--check-logs", action="store_true", help="Try to check OCR service logs")
    parser.add_argument("--log-dir", help="Path to OCR service log directory")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument("--skip-health-check", action="store_true", help="Skip server health check")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    file_path = Path(args.file).expanduser()

    # Pre-flight checks
    if not args.skip_health_check:
        if not check_server_health(args.base_url):
            print("\n  ⚠️  Server health check failed, but continuing...")
    
    if not check_file_access(file_path):
        return 1

    # Check logs before starting (optional)
    if args.check_logs:
        check_ocr_logs(args.log_dir)

    # Upload file
    uploaded_path = upload_file(args.base_url, file_path)
    if not uploaded_path:
        return 1

    # Verify uploaded file exists on server
    if uploaded_path and Path(uploaded_path).exists():
        print(f"  ✅ Verified uploaded file exists: {uploaded_path}")
    else:
        print(f"  ⚠️  Cannot verify uploaded file on server: {uploaded_path}")

    # Start task
    task_id = start_task(
        base_url=args.base_url,
        file_path=uploaded_path,
        prompt=args.prompt,
        vlm_prompt=args.vlm_prompt,
        use_qwen_vlm=not args.no_qwen_vlm,
        original_filename=file_path.name,
        output_dir=args.output_dir,
    )
    if not task_id:
        return 1

    # Wait for completion
    success, data = wait_for_completion(
        base_url=args.base_url,
        task_id=task_id,
        interval=args.interval,
        timeout=args.timeout,
        verbose=args.verbose,
    )

    if success:
        log_section("Result (/api/result)")
        print(json.dumps(data, indent=2, ensure_ascii=False))
        return 0

    # Task failed - show diagnostics
    log_section("Diagnostics")
    print("Task did not complete successfully.")
    if data:
        print("\nFull error response:")
        print(json.dumps(data, indent=2, ensure_ascii=False))
    
    # Check logs after failure
    if args.check_logs:
        print("\n")
        check_ocr_logs(args.log_dir)
    
    # Suggestions
    print("\n" + "=" * 80)
    print("  💡 Troubleshooting Suggestions:")
    print("=" * 80)
    print("  1. Check OCR service logs for detailed error messages")
    print("  2. Verify DeepSeek OCR model files are properly installed")
    print("  3. Check if the OCR service has write permissions to output directory")
    print("  4. Try without VLM: --no-qwen-vlm")
    print("  5. Check system resources (GPU/CPU memory)")
    print("  6. Verify the uploaded file is a valid PDF")
    print("=" * 80)
    
    return 1


if __name__ == "__main__":
    sys.exit(main())

