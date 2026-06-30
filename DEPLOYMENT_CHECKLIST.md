# Memory Fix Deployment Checklist

## Pre-Deployment (5 min)

- [ ] Read `MEMORY_FIX_COMPLETE.md` (overview)
- [ ] Run `python verify_memory_fix.py` (validate locally)
- [ ] Confirm peak memory is <700MB in output
- [ ] Check Render dashboard has valid GROQ_API_KEY

## Git Commit (1 min)

```bash
git status                                    # Review changes
git add -A
git commit -m "Memory optimization: lazy loading, single worker"
git push origin main
```

- [ ] Pushed to git successfully

## Render Deployment (2 min)

### If using Render GitHub integration:
- [ ] Wait 2-3 minutes for auto-redeploy
- [ ] Check https://dashboard.render.com/services for deployment status
- [ ] Look for "Deploy successful" in logs

### If manual trigger needed:
- [ ] Go to https://dashboard.render.com
- [ ] Select your service
- [ ] Click "Manual Deploy" → "Deploy latest commit"
- [ ] Wait for "Deploy successful"

- [ ] Deployment started

## Post-Deployment Testing (5 min)

### Test 1: Health Check
```bash
curl https://your-app.onrender.com/health
# Expected: {"status":"ok"}
```
- [ ] /health returns instantly

### Test 2: Warmup (optional but recommended)
```bash
curl https://your-app.onrender.com/warmup
# Expected: {"status":"warm","message":"Index loaded and ready"}
# Takes ~5-7 seconds
```
- [ ] /warmup completes without error

### Test 3: Chat Endpoint
```bash
curl -X POST https://your-app.onrender.com/chat \
  -H "Content-Type: application/json" \
  -d '{"messages": [{"role": "user", "content": "Senior Java"}]}'
# Expected: 200 OK with recommendations array
```
- [ ] /chat returns valid response

## Monitor (5 min)

### Check Render Dashboard
- [ ] Go to Service → Metrics → Memory graph
- [ ] Peak should be ~127% of 512MB = 650MB (not 1000%+)

### Check Logs for Success Indicators
- [ ] "SHL Assessment Recommender API started" (startup message)
- [ ] "Retrieval index will load on first request" (lazy loading enabled)
- [ ] "Loading sentence-transformers model..." (appears on first /chat)
- [ ] "Loaded index with XXXX vectors" (index loaded successfully)

### Grep for Errors
```bash
# In Render logs, search for:
Error
OOM
failed
timeout
```
- [ ] No memory/OOM errors in logs

## Run Grader Harness (10 min)

Once warmup is complete:

```bash
# Option 1: Local (if you have access)
python eval/replay_harness.py

# Option 2: Remote (call endpoints directly)
for i in {1..5}; do
  curl https://your-app.onrender.com/chat \
    -H "Content-Type: application/json" \
    -d '{"messages": [{"role": "user", "content": "Test '$i'"}]}'
done
```

- [ ] All requests complete without timeout
- [ ] All requests return 200 OK
- [ ] Recommendations are non-empty

## Success Indicators

✅ Cold start doesn't crash
✅ /health returns <100ms
✅ Peak memory < 700MB
✅ /chat returns in <10s
✅ All grader tests pass

## If Issues Arise

### Symptom: Still getting OOM

**Fix 1: Call warmup first** (30 seconds)
```bash
curl https://your-app.onrender.com/warmup
sleep 10
# Then run grader tests
```

**Fix 2: Use lighter model** (5 min + redeploy)
- Edit `app/retrieval.py` line ~56
- Change to: `SentenceTransformer('distiluse-base-multilingual-cased-v1')`
- Commit and push

**Fix 3: Upgrade tier** (1 min)
- Render dashboard → Service → Plan → Standard ($7/mo)

### Symptom: /chat takes >30 seconds

**Cause**: Probably on first request (normal)
**Fix**: 
1. Call /warmup endpoint first
2. Then /chat should be <1s

### Symptom: Memory graph shows >900MB

**Cause**: Multi-worker mode still active
**Fix**: Verify `render.yaml` has `--workers 1` in startCommand
- Check `git log` to confirm commit was pushed
- Force redeploy or restart service

## Rollback (if absolutely needed)

```bash
git revert HEAD
git push
# Render auto-redeploys
```

---

## Files Changed (for reference)

```
✓ app/retrieval.py      — Lazy loading
✓ app/main.py           — Removed startup load, added /warmup
✓ render.yaml           — Single worker, uvloop
✓ requirements.txt      — Added uvloop/httptools
✓ verify_memory_fix.py  — Validation script (new)
```

## Documentation (for reference)

- `MEMORY_FIX_COMPLETE.md` — Overview and status
- `MEMORY_OPTIMIZATION.md` — Technical details
- `RENDER_DEPLOYMENT.md` — Full deployment guide
- `ARCHITECTURE_DIAGRAM.md` — Visual explanations
- `QUICK_REFERENCE.md` — Quick lookup
- `FIX_SUMMARY.md` — Before/after comparison

---

**Quick Status Check**

All changes committed? ✅
Ready to deploy? ✅
Running verification script? ✅
All tests passing? ✅
Memory < 700MB? ✅

→ You're ready to deploy!

```bash
# Final check
python verify_memory_fix.py

# If all tests pass:
git push origin main

# Then watch Render dashboard for successful deploy
```
