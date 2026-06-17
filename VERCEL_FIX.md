# Vercel Deployment Fix: litellm Dependency Error

## Problem

When deploying the frontend to Vercel, you encountered this error:

```
Failed to run "uv lock --python /vercel/path0/.vercel/python/.venv/bin/python": 
Command failed: ...
× No solution found when resolving dependencies:
─▶ Because only the following versions of litellm are available: 
    litellm<=1.40.0 litellm==1.40.1 ... litellm==1.40.25
```

## Root Cause

The issue occurs because:

1. **Vercel is trying to build Python dependencies** - The root `vercel.json` was configured for the entire project, not just the frontend
2. **litellm is a Python package** - It's listed in `requirements.txt` for the backend, not the frontend
3. **Dependency conflict** - Vercel's Python environment couldn't resolve the litellm version due to conflicts with other Python packages

## Solution

The fix involves separating frontend and backend deployment configurations:

### 1. Updated Root `vercel.json`

The root configuration now properly targets only the frontend build:

```json
{
  "buildCommand": "cd frontend && npm run build",
  "outputDirectory": "frontend/dist",
  "devCommand": "cd frontend && npm run dev",
  "installCommand": "cd frontend && npm install",
  "framework": "vite",
  "rewrites": [
    {
      "source": "/(.*)",
      "destination": "/index.html"
    }
  ],
  "env": {
    "VITE_API_URL": "https://your-backend-url.railway.app"
  }
}
```

### 2. Created Frontend `.vercel/config.json`

Added a dedicated Vercel config for the frontend directory:

```json
{
  "buildCommand": "npm run build",
  "devCommand": "npm run dev",
  "installCommand": "npm install",
  "framework": "vite",
  "outputDirectory": "dist",
  "rewrites": [
    {
      "source": "/(.*)",
      "destination": "/index.html"
    }
  ],
  "env": {
    "VITE_API_URL": "https://your-backend-url.railway.app"
  }
}
```

### 3. Updated `.vercelignore` Files

Created `.vercelignore` files to exclude Python files and other unnecessary files from the frontend deployment:

**Root `.vercelignore`:**
- Excludes `.venv/`, `venv/`, `env/`, `*.py`, `requirements.txt`, `data/`, `neo4j/`, `qdrant/`, etc.

**Frontend `.vercelignore`:**
- Excludes `node_modules/`, `.env`, `dist/`, `build/`, `*.py`, `requirements.txt`, `data/`, `tests/`, etc.

## Deployment Steps

### Deploy Backend to Railway

1. Go to https://railway.app/new
2. Connect your GitHub repository
3. Add environment variables:
   ```
   NEO4J_URI=neo4j+s://your-neo4j-address
   NEO4J_USER=your_user
   NEO4J_PASSWORD=your_password
   QDRANT_API_KEY=your_key
   LITELLM_MODEL=openai/your-model
   LITELLM_API_BASE=https://api.your-llm-provider.com
   ```

### Deploy Frontend to Vercel

1. Go to https://vercel.com/new
2. Import your GitHub repository
3. **Important Settings**:
   - **Root Directory**: `frontend`
   - **Framework Preset**: Vite
   - **Build Command**: `npm run build`
   - **Output Directory**: `dist`
4. Add environment variable:
   ```
   VITE_API_URL=https://your-railway-backend-url.railway.app
   ```
5. Deploy!

## Alternative: Deploy Everything to Railway

If you prefer to deploy both frontend and backend together:

1. Go to https://railway.app/new
2. Connect your GitHub repo
3. **Add a second service** for frontend:
   - Click "New" → "Static Site"
   - Select your repo
   - Set root directory to `frontend`
4. Add all environment variables to both services

## Files Modified

1. `vercel.json` - Updated root configuration
2. `frontend/.vercel/config.json` - Created frontend-specific config
3. `.vercelignore` - Created root ignore file
4. `frontend/.vercelignore` - Created frontend ignore file

## Testing

After pushing these changes:

1. Vercel will automatically detect the changes
2. Go to your Vercel project dashboard
3. Click "Redeploy"
4. The build should now succeed without Python dependency errors

## Notes

- **Frontend is pure JavaScript/TypeScript** - It doesn't need Python dependencies
- **Backend handles all Python logic** - The FastAPI backend with litellm runs on Railway
- **Separation of concerns** - Frontend and backend are now properly separated in deployment
