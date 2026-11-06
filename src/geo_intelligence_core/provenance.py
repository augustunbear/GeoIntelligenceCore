"""Filesystem identity of the imported package's Python and JSON runtime inputs."""
import hashlib
from pathlib import Path


def package_fingerprint() -> str:
    root = Path(__file__).resolve().parent
    digest = hashlib.sha256()
    for file in sorted(root.rglob('*')):
        if file.is_file() and file.suffix in ('.py', '.json') and '__pycache__' not in file.parts:
            digest.update(file.relative_to(root).as_posix().encode() + b'\0' + file.read_bytes())
    return digest.hexdigest()
