"""Isolate conversion so the parent can enforce a deadline."""
import contextlib
import json
import sys

if __name__ == "__main__":
    with contextlib.redirect_stdout(sys.stderr):
        from markitdown import MarkItDown
        result = MarkItDown(enable_plugins=False).convert_local(sys.argv[1])
    cap = 8_000_000
    print(json.dumps({"text": result.text_content[:cap], "limited": len(result.text_content) > cap}, ensure_ascii=True))
