#!/usr/bin/env python3
"""Upload huggingface/dist/ to the Hugging Face dataset repo.

Needs HF_TOKEN with write access (a fine-grained or "write" token). Without it, this prints a
notice and exits 0, so a missing secret doesn't fail the workflow.

    HF_TOKEN=... python3 huggingface/publish.py
    HF_REPO=Arynwood/local-ai-benchmarks HF_PRIVATE=1 python3 huggingface/publish.py
"""
import os
import sys
from pathlib import Path

DIST = Path(__file__).resolve().parent / "dist"
REPO = os.environ.get("HF_REPO", "Arynwood/local-ai-benchmarks")


def main():
    token = os.environ.get("HF_TOKEN")
    if not token:
        print("::notice::HF_TOKEN is not set; skipping the Hugging Face upload.")
        return
    from huggingface_hub import HfApi

    api = HfApi(token=token)
    api.create_repo(REPO, repo_type="dataset", private=os.environ.get("HF_PRIVATE") == "1", exist_ok=True)
    sha = os.environ.get("GITHUB_SHA", "local")[:7]
    info = api.upload_folder(repo_id=REPO, repo_type="dataset", folder_path=DIST,
                             delete_patterns=["data/*", "raw/**"],
                             commit_message=f"Sync from GitHub {sha}")
    print(f"Uploaded to https://huggingface.co/datasets/{REPO} ({info.oid[:7] if info.oid else 'no changes'})")


if __name__ == "__main__":
    sys.exit(main())
