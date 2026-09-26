# Production Dockerfile for UPIAI Backend Engine
FROM python:3.11-slim

WORKDIR /app

# Install system build dependencies for C/C++ extensions & XGBoost
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libgomp1 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy dependency definition
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend, AI engine, and data layers
COPY ai /app/ai
COPY simulation /app/simulation
COPY data /app/data
COPY backend /app/backend

ENV PYTHONPATH=/app
ENV PORT=8000
ENV HOST=0.0.0.0
ENV ENVIRONMENT=production

EXPOSE 8000

CMD ["uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000"]
