# Deploying medknow Frontend to Vercel

## Prerequisites
- Vercel account (sign up at https://vercel.com)
- Vercel CLI installed globally: `npm install -g vercel`
- Or use Vercel Dashboard (no CLI needed)

## Option 1: Deploy via Vercel Dashboard (Recommended for Beginners)

### Step 1: Connect Your Repository
1. Go to https://vercel.com/new
2. Click "Import Git Repository"
3. Select your `medical-graphrag` repository
4. Click "Import"

### Step 2: Configure Project
Vercel will auto-detect:
- **Framework Preset**: Vite
- **Build Command**: `npm run build`
- **Output Directory**: `dist`
- **Install Command**: `npm install`

### Step 3: Add Environment Variables (Important!)
In the Vercel Dashboard, go to **Settings → Environment Variables**:

Add these variables:
```
VITE_API_URL=https://your-backend-url.com
```

Replace `https://your-backend-url.com` with your actual FastAPI backend URL.

### Step 4: Deploy
Click **Deploy** and wait for the build to complete.

Your app will be live at: `https://your-app-name.vercel.app`

---

## Option 2: Deploy via Vercel CLI

### Step 1: Login to Vercel
```bash
cd frontend
vercel login
```

### Step 2: Initialize Vercel Project
```bash
vercel
```

Follow the prompts:
- Set up and deploy? **Yes**
- Which scope? (select your account)
- Link to existing project? **No** (first time)
- Project name? **medknow** (or your preferred name)
- Directory? **.** (current directory)
- Override settings? **No**

### Step 3: Add Environment Variables
```bash
vercel env add VITE_API_URL production
```

Enter your backend URL when prompted.

### Step 4: Deploy
```bash
vercel --prod
```

---

## Post-Deployment Configuration

### 1. Update API URL
The frontend needs to know where your backend API is located.

**For local development:**
```bash
# In .env file
VITE_API_URL=http://localhost:8080
```

**For production:**
Update `VITE_API_URL` in Vercel Dashboard to your backend URL:
- If backend is also on Vercel: `https://your-backend-project.vercel.app`
- If backend is on another service: `https://api.yourdomain.com`

### 2. CORS Configuration (Backend)
Ensure your FastAPI backend allows CORS from Vercel:

```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://your-app.vercel.app"],  # Update with your Vercel URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### 3. Custom Domain (Optional)
1. Go to Vercel Dashboard → Your Project → Settings → Domains
2. Add your custom domain
3. Update DNS records as instructed

---

## Troubleshooting

### Build Fails
```bash
# Clean and rebuild
rm -rf node_modules package-lock.json
npm install
npm run build
```

### API Calls Fail After Deployment
- Check that `VITE_API_URL` is set correctly in Vercel Dashboard
- Verify your backend URL is accessible
- Check CORS settings on the backend

### 404 on Page Reload
- The `vercel.json` file handles SPA routing
- Ensure it's in the root of the `frontend` directory

---

## Environment Variables Reference

| Variable | Description | Example |
|----------|-------------|---------|
| `VITE_API_URL` | Backend API endpoint | `https://api.medknow.com` |

---

## Next Steps

1. ✅ Deploy frontend to Vercel
2. ⏳ Deploy backend to a service (Vercel, Railway, Render, etc.)
3. ⏳ Configure CORS on backend
4. ⏳ Update `VITE_API_URL` environment variable
5. ⏳ Test the full application

## Useful Commands

```bash
# Preview production build
npm run preview

# Check build output
npm run build
ls dist/

# Deploy with CLI
vercel --prod
```
