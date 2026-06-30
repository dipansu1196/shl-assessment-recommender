# Deployment Guide - Task 11

## 🚀 Deploy to Render (FastAPI API)

### ⚠️ CRITICAL: GROQ_API_KEY Setup

**READ THIS FIRST**: The `GROQ_API_KEY` environment variable MUST be set in Render's dashboard AFTER deployment. It is NOT hardcoded anywhere. Follow the exact steps below.

---

## Step 1: Prepare Your Repository

### Ensure `.env` is NOT committed

```bash
# Verify .env is in .gitignore
cat .gitignore | grep "^\.env$"

# Should output: .env
```

### Commit your code to GitHub

```bash
git init
git add .
git commit -m "SHL Assessment Recommender API"
git remote add origin https://github.com/YOUR_USERNAME/shl-recommender.git
git push -u origin main
```

### Verify these files are in your repo

```
✓ render.yaml                 # Deployment config
✓ requirements.txt            # Dependencies
✓ app/main.py                # FastAPI app
✓ .env.example               # Template (NOT .env)
✓ .gitignore                 # Excludes .env
```

---

## Step 2: Create Render Account

1. Go to **https://render.com**
2. Click **Sign Up**
3. Sign up with GitHub account
4. Authorize Render to access your repositories

---

## Step 3: Create Web Service on Render

1. Click **New** button
2. Select **Web Service**
3. Choose your `shl-recommender` repository
4. Render will auto-detect `render.yaml`
5. Click **Create Web Service**
6. Wait 2-3 minutes for deployment

**You'll see logs like:**
```
Building application...
Installing dependencies...
Building complete
Starting application...
Service started
```

---

## Step 4: Set GROQ_API_KEY (CRITICAL - DO THIS NOW)

**⚠️ THIS IS THE MOST IMPORTANT STEP - SKIP THIS AND YOUR API WON'T WORK**

### Navigate to Environment Variables

1. In Render dashboard, find your service
2. Click the service name
3. Click **Environment** tab (left sidebar)

### Add the Secret

1. Click **Add Environment Variable**
2. Fill in:
   - **Key**: `GROQ_API_KEY`
   - **Value**: Your API key from https://console.groq.com (paste exactly: `gsk_...`)
3. Leave **"Show in build logs"** OFF (for security)
4. Click **Save**

### Service Auto-Restarts

After saving, Render automatically:
- Restarts the service
- Injects the environment variable
- Makes it available to the application

**You should see logs:**
```
Service updated
Restarting application...
```

---

## Step 5: Test Your Deployed API

### Get Your API URL

In Render dashboard, look for your service URL. It will be like:
```
https://shl-recommender-abc123.onrender.com
```

### Test Health Check

```bash
curl -X GET https://shl-recommender-abc123.onrender.com/health
```

**Should return:**
```json
{"status": "ok"}
```

### Test Chat Endpoint

```bash
curl -X POST https://shl-recommender-abc123.onrender.com/chat \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [
      {"role": "user", "content": "I need assessments for senior developers"}
    ]
  }'
```

**Should return:**
```json
{
  "reply": "To help narrow this down...",
  "recommendations": [],
  "end_of_conversation": false
}
```

### Test Swagger UI

Open in browser:
```
https://shl-recommender-abc123.onrender.com/docs
```

---

## Understanding render.yaml

```yaml
services:
  - type: web                              # Web service
    name: shl-assessment-recommender       # Service name
    runtime: python311                     # Python 3.11
    plan: free                             # Free tier
    buildCommand: pip install -r requirements.txt
    startCommand: uvicorn app.main:app --host 0.0.0.0 --port $PORT
    envVars:
      - key: GROQ_API_KEY                  # Variable name
        scope: run                         # Available at runtime
        sync: false                        # Don't sync to other processes
```

**Key Points:**
- `$PORT` is set by Render (usually 10000)
- Build command runs once
- Start command runs the API
- Environment variable is injected at runtime (not in logs)

---

## Deploy Streamlit Demo (Optional)

The Streamlit demo UI can call your Render API.

### Option A: Use Demo at HF Spaces

1. Go to **https://huggingface.co/spaces**
2. Click **Create new Space**
3. Name: `shl-recommender-demo`
4. SDK: **Streamlit** (select this!)
5. Create Space

### Upload Streamlit Files

In the Space, upload:
- `streamlit_demo/app.py` → rename to `app.py` (must be at root)
- `streamlit_demo/README.md` → for reference

### Set API URL

In HF Spaces → Settings → Secrets, add:
- Name: `API_URL`
- Value: Your Render URL (e.g., `https://shl-recommender-abc123.onrender.com`)

### Access Demo

Your Space will be at:
```
https://huggingface.co/spaces/YOUR_USERNAME/shl-recommender-demo
```

---

## Troubleshooting

### "GROQ_API_KEY not found"

**This means you haven't set it in Render's dashboard yet.**

1. Go to your Render service
2. Click **Environment** tab
3. Add the variable with your actual API key
4. Service will restart automatically

### "Connection refused" or "502 Bad Gateway"

- Service is starting (takes 1-2 min)
- Check Render logs for errors
- Verify GROQ_API_KEY is set
- Wait another minute and try again

### "Timeout after 30 seconds"

- First request triggers FAISS index load (~30s)
- Subsequent requests are faster (~2-3s)
- Free tier might sleep after 15 min inactivity

### "Internal Server Error"

1. Check Render logs
2. Verify GROQ_API_KEY is set correctly
3. Try health check: `curl https://your-url/health`

---

## Local Development vs Deployed

### Local (Before Deploy)

```bash
# 1. Install
pip install -r requirements.txt

# 2. Build index
cd data && python build_index.py && cd ..

# 3. Start
python -m uvicorn app.main:app --port 8000

# 4. Test
curl http://localhost:8000/health
```

### Deployed on Render

```bash
# No manual steps needed!
# 1. Render builds automatically from requirements.txt
# 2. Index is loaded from pre-built files
# 3. API starts automatically
# 4. Test at your Render URL
curl https://your-render-url/health
```

---

## Deployment Checklist

### Before Deploy
- [ ] Code committed to GitHub
- [ ] `.env` in `.gitignore`
- [ ] `render.yaml` in repository root
- [ ] `requirements.txt` has all dependencies
- [ ] Local tests pass: `pytest tests/ -v`
- [ ] Local API works: `python -m uvicorn app.main:app --port 8000`

### After Deploy
- [ ] Render service created successfully
- [ ] **GROQ_API_KEY set in Render Environment Variables**
- [ ] Health check returns 200
- [ ] Chat endpoint works
- [ ] Swagger UI loads at `/docs`

### Optional Streamlit Demo
- [ ] HF Space created
- [ ] `app.py` uploaded to root
- [ ] `API_URL` environment variable set
- [ ] Space deploys successfully
- [ ] Demo UI calls Render API

---

## Security Reminders

❌ **DO NOT:**
- Commit `.env` file
- Hardcode API keys in code
- Set secrets in `render.yaml` values
- Show API key in logs or error messages

✅ **DO:**
- Use `.env.example` as template
- Set secrets in Render's dashboard
- Mark secrets as sensitive (scope: run)
- Use environment variables for all secrets

---

## Production Next Steps

1. Upgrade from free tier to paid for uptime guarantee
2. Add monitoring and alerts
3. Enable request logging
4. Set up rate limiting
5. Add authentication if needed
6. Monitor Groq API costs

---

## Useful Links

- **Render**: https://render.com
- **Render Docs**: https://render.com/docs
- **HF Spaces**: https://huggingface.co/spaces
- **FastAPI Docs**: https://fastapi.tiangolo.com
- **Groq API**: https://console.groq.com

---

## Getting Help

If deployment fails:

1. Check Render service logs (full output)
2. Verify GROQ_API_KEY is set
3. Test locally first: `python -m uvicorn app.main:app --port 8000`
4. Check requirements.txt has all dependencies
5. Verify render.yaml is in repository root

---

**NOW GO SET GROQ_API_KEY IN RENDER DASHBOARD IF YOU HAVEN'T ALREADY!** 🔑

---
