from __future__ import annotations

import hashlib
from pathlib import Path
import shutil


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def ensure_profile_dirs(base_docs: Path, profile_id: str) -> dict[str, Path]:
    root = base_docs / profile_id
    dirs = {
        "root": root,
        "originals": root / "originals",
        "pdf": root / "pdf",
        "preview": root / "preview",
    }
    for d in dirs.values():
        d.mkdir(parents=True, exist_ok=True)
    return dirs


def copy_file(src: Path, dst: Path) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)
