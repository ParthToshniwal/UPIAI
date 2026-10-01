"""
UPIAI Streamlit Dashboard Launcher.
Launches the multi-tab frontend connected to the FastAPI backend.
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

import subprocess

if __name__ == "__main__":
    print("=" * 65)
    print("[UPIAI] Launching UPIAI Streamlit Dashboard...")
    print("[UPIAI] Web Dashboard URL: http://localhost:8501")
    print("=" * 65)
    
    app_path = os.path.join(os.path.dirname(__file__), "streamlit_app", "app.py")
    subprocess.run([sys.executable, "-m", "streamlit", "run", app_path])
