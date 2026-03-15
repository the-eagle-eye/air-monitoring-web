"""Rollback ML artifacts from a backup directory.

Usage:
    python scripts/rollback_artifacts.py [--backup-dir PATH]
"""

import argparse
import json
import shutil
from pathlib import Path


def find_latest_backup(base_dir: str = ".") -> Path | None:
    """Find the most recent ml_artifacts_backup_* directory."""
    base = Path(base_dir)
    backups = sorted(base.glob("ml_artifacts_backup_*"), reverse=True)
    return backups[0] if backups else None


def rollback(backup_dir: str | None = None, artifacts_dir: str = "ml_artifacts"):
    if backup_dir:
        src = Path(backup_dir)
    else:
        src = find_latest_backup()

    if not src or not src.exists():
        print("ERROR: No backup directory found.")
        print("  Specify --backup-dir or ensure ml_artifacts_backup_* exists.")
        return False

    dest = Path(artifacts_dir)

    # Show what we're restoring
    metadata_path = src / "model_metadata.json"
    if metadata_path.exists():
        with open(metadata_path) as f:
            meta = json.load(f)
        print(f"Restoring from: {src}")
        print(f"  Model version: {meta.get('model_version', 'unknown')}")
        print(f"  Trained at: {meta.get('trained_at', 'unknown')}")
    else:
        print(f"Restoring from: {src} (no metadata found)")

    # Remove current artifacts and copy backup
    if dest.exists():
        shutil.rmtree(dest)
    shutil.copytree(src, dest)

    print(f"Artifacts restored to {dest}/")
    return True


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Rollback ML artifacts")
    parser.add_argument("--backup-dir", default=None, help="Specific backup directory")
    parser.add_argument(
        "--artifacts-dir", default="ml_artifacts", help="Target artifacts directory"
    )
    args = parser.parse_args()
    rollback(args.backup_dir, args.artifacts_dir)
