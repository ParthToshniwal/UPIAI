"""
UPIAI Backend Server Launcher (from backend directory).
"""

import os
import sys

# Force UTF-8 encoding on Windows console
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

import uvicorn

backend_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.abspath(os.path.join(backend_dir, ".."))

for p in [root_dir, backend_dir]:
    if p not in sys.path:
        sys.path.insert(0, p)

if __name__ == "__main__":
    print("=" * 65)
    print("[UPIAI] Starting UPIAI Backend Server...")
    print("[UPIAI] Swagger API Docs: http://127.0.0.1:8000/docs")
    print("=" * 65)
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=True)
