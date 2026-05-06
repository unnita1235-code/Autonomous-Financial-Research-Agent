# Deployment Guide

## Backend: Render (Free Tier)
- Platform: https://render.com
- Deploy method: Connect GitHub repo → auto-deploy on push
- Start command: uvicorn app.main:app --host 0.0.0.0 --port $PORT
- Health check: /health
- Free tier note: Spins down after 15 min inactivity.
  First request after spin-down takes ~30 seconds (cold start). Normal.
- Required env vars (set in Render dashboard):
  - DATABASE_URL
  - GROQ_API_KEY
  - NEWS_API_KEY
  - ALPHA_VANTAGE_KEY
  - LLM_PROVIDER=groq
  - ALLOWED_ORIGINS=https://your-vercel-url.vercel.app
