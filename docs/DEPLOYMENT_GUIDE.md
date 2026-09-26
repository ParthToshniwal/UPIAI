# UPIAI Production Deployment & Vercel Integration Guide

This guide details how to deploy the **UPIAI Next.js Frontend on Vercel** and connect it to the **FastAPI AI ML Backend**.

---

## 🏗️ Architecture Overview

```
┌────────────────────────────────────────────────────────┐
│               VERCEL CLOUD (Edge Network)               │
│  Next.js 14 Dashboard • Recharts Visualizer • Tailwind  │
│  URL: https://upiai.vercel.app                         │
└──────────────────────────┬─────────────────────────────┘
                           │
                           │ HTTPS API Requests (REST / JSON)
                           ▼
┌────────────────────────────────────────────────────────┐
│       AI BACKEND ENGINE (Render / Railway / AWS / Docker)│
│  FastAPI • XGBoost • Schema Mapper • Readiness Auditor │
│  URL: https://upiai-api.onrender.com (or local tunnel)  │
└──────────────────────────┬─────────────────────────────┘
                           │
                           │ Motor Async Driver / PyMongo
                           ▼
┌────────────────────────────────────────────────────────┐
│             MONGODB ATLAS (Cloud Cluster)              │
│  Collections: sales, inventory, suppliers, feedback    │
└────────────────────────────────────────────────────────┘
```

---

## 🚀 Step 1: Deploy the Frontend to Vercel

### Method A: Deploy via GitHub (Recommended)

1. **Push your code to GitHub**:
   ```bash
   git init
   git add .
   git commit -m "feat: UPIAI full stack production release"
   git branch -M main
   git remote add origin https://github.com/<YOUR_USERNAME>/UPIAI.git
   git push -u origin main
   ```

2. **Import into Vercel**:
   - Navigate to [vercel.com/new](https://vercel.com/new).
   - Select your `UPIAI` repository.
   - Set **Root Directory** to `frontend` (Click *Edit* next to Root Directory and select `frontend`).
   - **Framework Preset**: `Next.js` (automatically detected).

3. **Configure Environment Variables**:
   - Key: `NEXT_PUBLIC_API_URL`
   - Value: `https://<YOUR_BACKEND_URL>` (e.g. `https://upiai-api.onrender.com` or your live backend URL).

4. **Click Deploy**:
   - Vercel will run `npm install` and `npm run build` to generate the global edge deployment.

---

### Method B: Deploy via Vercel CLI

In your terminal:
```bash
cd frontend
npx vercel
```
- Follow the interactive prompts.
- When prompted for project settings, choose default options.
- Set `NEXT_PUBLIC_API_URL` when prompted or in the Vercel dashboard.

---

## 🐍 Step 2: Deploy the FastAPI AI Backend

Choose one of the following deployment options for the Python ML backend:

### Option 1: Free 1-Click Deploy on Render.com (Recommended)

1. Sign up at [render.com](https://render.com).
2. Click **New +** -> **Web Service** -> Connect your GitHub repo.
3. Configure settings:
   - **Name**: `upiai-backend`
   - **Environment**: `Python`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn backend.app.main:app --host 0.0.0.0 --port $PORT`
4. Add **Environment Variables**:
   - `MONGO_URI`: `mongodb+srv://<user>:<password>@cluster0.mongodb.net/upiai_db?retryWrites=true&w=majority`
   - `DATABASE_NAME`: `upiai_db`
   - `ALLOWED_ORIGINS`: `https://*.vercel.app,http://localhost:3000`
5. Click **Create Web Service**.
6. Copy your live Render URL (e.g., `https://upiai-backend.onrender.com`) and paste it as `NEXT_PUBLIC_API_URL` in your Vercel project settings.

---

### Option 2: Docker Container on Railway / Cloud Run / Fly.io

Use the pre-built `Dockerfile` at the root of the project:
```bash
# Build container image
docker build -t upiai-backend .

# Run locally to test
docker run -p 8000:8000 -e MONGO_URI="mongodb://localhost:27017/upiai_db" upiai-backend
```

---

### Option 3: Instant Live Testing via Tunnel (Zero Cloud Setup)

If you want to test your Vercel frontend against your local backend immediately:

1. Start your local FastAPI backend:
   ```bash
   cd backend
   ..\.venv\Scripts\Activate.ps1
   uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
   ```

2. In another terminal, create an HTTPS tunnel using `ngrok` or `localtunnel`:
   ```bash
   # Using ngrok:
   ngrok http 8000

   # Or using npx localtunnel:
   npx localtunnel --port 8000
   ```

3. Copy the generated HTTPS URL (e.g. `https://random-id.ngrok-free.app`) and set it as `NEXT_PUBLIC_API_URL` in Vercel.

---

## 🔒 Step 3: CORS & Security Checklist

The FastAPI backend automatically permits:
- `http://localhost:3000` (Local Next.js)
- `https://*.vercel.app` (All Vercel preview & production branches)
- Any custom domain specified in `ALLOWED_ORIGINS`.

---

## 🧪 Verification

Once deployed:
1. Open your Vercel URL (e.g. `https://upiai.vercel.app`).
2. Verify the top right status badge shows **"FastAPI & ML Core Active"** (green indicator).
3. Try generating a 7-day or 30-day forecast, running a What-If simulation, or dispatching a Purchase Order.
