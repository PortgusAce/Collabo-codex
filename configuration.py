"""Small local configuration helpers; never expose configuration writes as MCP tools."""
import json
import os
from pathlib import Path
import tempfile

BASE = Path(__file__).resolve().parent
RUNTIME = BASE / ".runtime"
FILES_CONFIG = RUNTIME / "files.json"


def read_json(path, default=None):
    path = Path(path)
    return json.loads(path.read_text(encoding="utf-8-sig")) if path.exists() else default


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(dir=path.parent, prefix=path.name, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(value, stream, ensure_ascii=False, indent=2)
            stream.write("\n")
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def validate_file_config(config):
    roots = config.get("roots", [])
    if not isinstance(roots, list) or not all(isinstance(p, str) for p in roots):
        raise ValueError("roots must be a list of absolute local directory paths")
    normalized = []
    for value in roots:
        path = Path(value).expanduser()
        if not path.is_absolute() or value.startswith(("\\\\", "//")) or "://" in value:
            raise ValueError("Each root must be an absolute local directory, not a URL or network share")
        if path.exists() and not path.is_dir():
            raise ValueError("A root must be a directory")
        value = str(path.resolve())
        if value not in normalized:
            normalized.append(value)
    size, timeout = config.get("max_file_mb", 64), config.get("conversion_timeout_seconds", 45)
    if isinstance(size, bool) or not isinstance(size, int) or not 1 <= size <= 256:
        raise ValueError("max_file_mb must be an integer from 1 to 256")
    if isinstance(timeout, bool) or not isinstance(timeout, int) or not 1 <= timeout <= 120:
        raise ValueError("conversion_timeout_seconds must be an integer from 1 to 120")
    return {"roots": normalized, "max_file_mb": size, "conversion_timeout_seconds": timeout}
