"""
UPIAI Streamlit Dashboard & Unified Backend Launcher.
Automatically boots the FastAPI demand intelligence backend on port 8000
and launches the multi-tab executive Streamlit frontend on port 8501.
"""

import os
import sys
import time

# Force UTF-8 encoding on Windows console
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

import subprocess

# Ensure workspace root and modules are in sys.path
root_dir = os.path.dirname(os.path.abspath(__file__))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

# Import backend bridge supervisor
try:
    from streamlit_app.backend_bridge import (
        find_python_interpreter,
        ensure_backend_running,
        is_backend_alive
    )
except ImportError:
    # Fallback path injection
    sys.path.insert(0, os.path.join(root_dir, "streamlit_app"))
    from backend_bridge import (
        find_python_interpreter,
        ensure_backend_running,
        is_backend_alive
    )

if __name__ == "__main__":
    print("=" * 70)
    print("⚡ [UPIAI] Unified Demand Intelligence & Retail Analytics Platform")
    print("=" * 70)

    python_exe = find_python_interpreter()
    print(f"[*] Python Interpreter: {python_exe}")

    # 1. Check and start backend
    print("[*] Probing FastAPI backend server (http://127.0.0.1:8000)...")
    alive, _ = is_backend_alive("http://127.0.0.1:8000", timeout=0.6)
    if not alive:
        print("[*] Auto-starting UPIAI backend server with Turso DB & XGBoost...")
        meta = ensure_backend_running(api_base_url="http://127.0.0.1:8000", max_wait_seconds=8.0)
        if meta.get("online"):
            print("    [OK] Backend server is ONLINE and responsive!")
        else:
            print("    [!] Backend initializing in background; frontend will use direct engine.")
    else:
        print("    [OK] Backend is already running!")

    print("[*] Backend Swagger Docs: http://127.0.0.1:8000/docs")
    print("[*] Launching Streamlit Executive Dashboard (http://localhost:8501)...")
    print("=" * 70)

    app_path = os.path.join(root_dir, "streamlit_app", "app.py")
    subprocess.run([python_exe, "-m", "streamlit", "run", app_path])
