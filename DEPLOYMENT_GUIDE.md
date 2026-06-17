# Deployment Guide: medknow Frontend + Backend

## Architecture Overview

```
┌─────────────┐         ┌──────────────┐         ┌─────────────┐
│   Frontend  │ ──────► │   Backend    │ ──────► │  Databases  │
│  (Vercel)   │  HTTP   │  (Railway)   │  RPC    │ Neo4j/Qdrant│
└─────────────┘         └──────────────┘         └─────────────┘
```

## Option 1: Frontend on Vercel + Backend on Railway (Recommended)

### Step 1: Deploy Backend to Railway

1. Go to https://railway.app/new
2. Connect your GitHub repository (`avanthika-ileaf/medical-graphrag`)
3. Railway will auto-detect the FastAPI app
4. **Add environment variables** in Railway dashboard:
   ```
   NEO4J_URI=neo4j+s://your-neo4j-address
   NEO4J_USER=your_user
   NEO4J_PASSWORD=your_password
   QDRANT_API_KEY=your_key
   LITELLM_MODEL=openai/your-model
   REGOLO_API_KEY=your_key
   LITELLM_API_BASE=https://api.your-llm-provider.com
   ```
5. Deploy! Railway will build and run your backend.

### Step 2: Deploy Frontend to Vercel

1. Go to https://vercel.com/new
2. Import your GitHub repository
3. **Important Settings**:
   - **Root Directory**: `frontend` (this is crucial!)
   - **Framework Preset**: Vite
   - **Build Command**: `npm run build`
   - **Output Directory**: `dist`
4. **Add environment variable**:
   ```
   VITE_API_URL=https://your-railway-backend-url.railway.app
   ```
5. Deploy!

### Step 3: Connect Frontend to Backend

Update `frontend/.env`:
```env
VITE_API_URL=https://your-deployed-backend.railway.app
```

## Option 2: Deploy Everything to Railway (Alternative)

If you want to deploy both frontend and backend together:

1. Go to https://railway.app/new
2. Connect your GitHub repo
3. **Add a second service** for frontend:
   - Click "New" → "Static Site"
   - Select your repo
   - Set root directory to `frontend`
4. Add all environment variables to both services

## Quick Deploy Commands

### Backend (Railway)
```bash
# Railway will auto-deploy from GitHub, no CLI needed
# Just connect repo at https://railway.app/new
```

### Frontend (Vercel CLI - Optional)
```bash
# Install Vercel CLI
npm i -g vercel

# Login
vercel login

# Deploy frontend only
cd frontend
vercel --prod
```

## Environment Variables Summary

### Backend (.env)
```env
# Database
NEO4J_URI=neo4j+s://...
NEO4J_USER=...
NEO4J_PASSWORD=...

# Vector Database
QDRANT_API_KEY=...

# LLM
LITELLM_MODEL=openai/...
REGOLO_API_KEY=...
LITELLM_API_BASE=...
```

### Frontend (.env - in Vercel dashboard)
```env
VITE_API_URL=https://your-backend-url.railway.app
```

## Troubleshooting

### Issue: CORS errors in frontend
**Solution**: Update backend CORS configuration in `api/dependencies.py`

### Issue: Backend can't connect to Neo4j
**Solution**: Ensure `NEO4J_URI` uses `neo4j+s://` prefix for cloud Neo4j

### Issue: Vercel tries to deploy backend
**Solution**: Make sure "Root Directory" is set to `frontend` in Vercel dashboard

## Next Steps

1. ✅ Create Neo4j database (https://neo4j.com/cloud/sign-up/)
2. ✅ Create Qdrant instance (https://cloud.qdrant.io/)
3. ✅ Get LLM API keys (OpenAI, Anthropic, etc.)
4. Deploy backend to Railway
5. Deploy frontend to Vercel
6. Update `VITE_API_URL` in frontend
7. Test the full application!
