"""Backup ML artifacts before retraining.

Usage:
    python scripts/backup_artifacts.py [--artifacts-dir PATH]
"""

import argparse
import shutil
from datetime import datetime, timezone
from pathlib import Path


def backup(artifacts_dir: str = "ml_artifacts") -> str:
    src = Path(artifacts_dir)
    if not src.exists():
        raise FileNotFoundError(f"Artifacts directory not found: {src}")

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    dest = src.parent / f"{src.name}_backup_{timestamp}"
    shutil.copytree(src, dest)
    print(f"Backup created: {dest}")
    return str(dest)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Backup ML artifacts")
    parser.add_argument(
        "--artifacts-dir", default="ml_artifacts", help="Path to artifacts directory"
    )
    args = parser.parse_args()
    backup(args.artifacts_dir)
