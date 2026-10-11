"""
UPIAI - Root FastAPI Entrypoint for Vercel Serverless Deployment.
Exposes the ASGI `app` instance from backend.app.main for Vercel CLI.
"""

import os
import sys

# Ensure root workspace and backend dir are in PYTHONPATH
root_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.join(root_dir, "backend")

for p in [root_dir, backend_dir]:
    if p not in sys.path:
        sys.path.insert(0, p)

from backend.app.main import app

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)
