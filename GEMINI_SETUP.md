# 🔑 Google Gemini API Setup Guide

## Overview
The FDS-2-Matrix application can use Google's Gemini API to search online for missing chemical product information (CAS numbers, UN numbers, classifications, etc.).

## Security
Your API key is stored **locally only** and never committed to git:
- ✅ API key in `.env.local` (git-ignored)
- ✅ Never exposed in public repositories
- ✅ Protected by `.gitignore` rules

## Setup Instructions

### 1. Get Your Google API Key
1. Go to [Google AI Studio](https://aistudio.google.com/app/apikey)
2. Sign in with your Google account
3. Click **"Create API key"**
4. Copy your API key

### 2. Create `.env.local` File
```bash
cp .env.local.example .env.local
```

### 3. Add Your API Key
Edit `.env.local` and replace `your_api_key_here` with your actual key:
```env
GOOGLE_API_KEY=AIzaSyCE8MaDp6t4UP6jG9N_VB5hbLcV0AT7wxg
```

### 4. Verify Configuration
```bash
source .venv/bin/activate
python -c "
from src.utils.config import GEMINI_CONFIG
if GEMINI_CONFIG.get('api_key'):
    print('✅ API Key loaded successfully!')
else:
    print('❌ API Key not found - check .env.local')
"
```

## Features Enabled with Gemini

When your API key is configured, the application will:

### Online Search for Missing Fields
After extracting data from a PDF, if certain fields are missing, Gemini will search online for:
- **Product Name** (nome_produto)
- **Manufacturer** (fabricante)
- **UN Number** (numero_onu)
- **CAS Number** (numero_cas)
- **UN Classification** (classificacao_onu)
- **Packing Group** (grupo_embalagem)
- **Incompatibilities** (incompatibilidades)

### How It Works
1. Local LLM (phi3:mini) extracts info from PDF
2. If fields are missing, Gemini searches online
3. Results are merged and stored in database
4. Confidence scores indicate reliability

## File Structure
```
project/
├── .env              # Shared config (committed)
├── .env.local        # Local secrets (git-ignored)
├── .env.local.example # Template for .env.local
└── src/utils/config.py # Loads both .env files
```

## Configuration Priority
1. `.env` - Default settings (committed)
2. `.env.local` - Local overrides (git-ignored)

Variables in `.env.local` override `.env`.

## Troubleshooting

### API Key Not Loading
```bash
# Check if .env.local exists and is readable
ls -l .env.local

# Verify config
python -c "import os; print(os.getenv('GOOGLE_API_KEY'))"
```

### Rate Limiting
Gemini API has rate limits. If you hit them:
1. Wait a few minutes and retry
2. Check your billing settings at [Google Cloud Console](https://console.cloud.google.com/)
3. Upgrade your plan if needed

### Invalid API Key Error
- Verify the key is correct in `.env.local`
- Make sure `.env.local` has proper line endings (Unix, not Windows)
- Test the key at Google AI Studio

## Cost Considerations
- Gemini API is **free with usage limits**
- Each online search costs a small number of API credits
- Monitor your usage at [Google API Dashboard](https://console.cloud.google.com/)

## Privacy & Security
- API key never leaves your local machine
- All processing happens on your server
- Results stored in local DuckDB database
- No data sent to GitHub (`.env.local` is git-ignored)

## Disabling Gemini

To disable online searches, comment out in `.env`:
```env
# ONLINE_SEARCH_PROVIDER=gemini
ONLINE_SEARCH_PROVIDER=none
```

Or keep `.env.local` empty - fallback to local-only processing.

---

**Version:** 1.0
**Date:** 18 de Novembro de 2025
**Status:** Production Ready
