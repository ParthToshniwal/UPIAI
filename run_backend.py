"""
UPIAI Backend Server Launcher.
Runs FastAPI with Uvicorn, initializes Turso (libsql) database,
and serves all AI forecasting & DMart analytics endpoints.
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

# Inject paths
root_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.join(root_dir, "backend")

for p in [root_dir, backend_dir]:
    if p not in sys.path:
        sys.path.insert(0, p)

if __name__ == "__main__":
    print("=" * 65)
    print("[UPIAI] Starting UPIAI Demand Intelligence Backend...")
    print("[UPIAI] Database: Turso (libsql) / SQLite Embedded Engine")
    print("[UPIAI] Swagger API Docs: http://127.0.0.1:8000/docs")
    print("[UPIAI] Health Check:     http://127.0.0.1:8000/health")
    print("=" * 65)
    
    port = int(os.getenv("PORT", 8000))
    host = os.getenv("HOST", "127.0.0.1")
    reload_flag = os.getenv("RELOAD", "false").lower() in ("true", "1", "yes") or "--reload" in sys.argv
    
    if reload_flag:
        uvicorn.run("backend.app.main:app", host=host, port=port, reload=True)
    else:
        from backend.app.main import app
        uvicorn.run(app, host=host, port=port)
