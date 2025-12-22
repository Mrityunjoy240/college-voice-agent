# 🚀 Quick Start Guide - College Info Voice Agent

## Step 1: Navigate to Project

```bash
cd c:\Users\ANAMIKA\OneDrive\Desktop\college\college-agent
```

## Step 2: Install Frontend Dependencies

```bash
cd frontend
npm install
cd ..
```

## Step 3: Configure API Keys (Optional for Testing)

The system will work without API keys for basic testing. To enable full voice features:

1. Get API keys:
   - **AssemblyAI**: https://www.assemblyai.com/ (Real-time STT)
   - **MURF.ai**: https://murf.ai/ (TTS)

2. Edit `backend\.env` and replace placeholders:
   ```env
   ASSEMBLYAI_API_KEY=your_actual_key_here
   MURF_API_KEY=your_actual_key_here
   ```

## Step 4: Start with Docker (Recommended)

```bash
# Start all services
docker-compose up -d

# Wait 30 seconds for services to initialize

# Pull OLLAMA model (required, ~2GB download)
docker exec -it college-ollama ollama pull llama3.2:3b
```

**OR** Start Locally (Without Docker):

### Backend:
```bash
cd backend
pip install -r requirements.txt

# Install and start OLLAMA separately
# Download from: https://ollama.ai/
ollama serve
ollama pull llama3.2:3b

# In another terminal
uvicorn app.main:app --reload
```

### Frontend:
```bash
cd frontend
npm run dev
```

## Step 5: Access the Application

- **Voice Chat**: http://localhost:5173
- **Admin Dashboard**: http://localhost:5173/admin
- **API Documentation**: http://localhost:8000/docs

## Step 6: Upload Documents

1. Go to http://localhost:5173/admin
2. Click "Choose File"
3. Upload college documents (PDF, Excel, CSV, or TXT)
4. Wait for processing to complete

## Step 7: Test Voice Chat

1. Go to http://localhost:5173
2. Click the microphone button (🎤)
3. Allow microphone access
4. Speak your question: "What is the BTech fee?"
5. Get instant answer with sources!

## 🎯 What Works Without API Keys

✅ **Text-based queries** (type questions)
✅ **Document upload and processing**
✅ **RAG with OLLAMA** (local LLM)
✅ **Web Speech API** (browser voice recognition)
✅ **Admin dashboard**

❌ **AssemblyAI real-time STT** (needs API key)
❌ **MURF.ai TTS audio** (needs API key)

## 🔧 Troubleshooting

### OLLAMA not responding
```bash
# Check OLLAMA status
docker logs college-ollama

# Restart OLLAMA
docker restart college-ollama
```

### Frontend not loading
```bash
# Reinstall dependencies
cd frontend
rm -rf node_modules package-lock.json
npm install
```

### Port already in use
```bash
# Stop all containers
docker-compose down

# Check what's using the port
netstat -ano | findstr :8000
netstat -ano | findstr :5173
```

## 📊 System Requirements

- **RAM**: 4GB minimum (8GB recommended)
- **Disk**: 5GB free space
- **OS**: Windows 10/11, macOS, Linux
- **Browser**: Chrome, Edge, or Safari (for voice features)

## 🎉 You're Ready!

Your College Info Voice Agent is now running! Upload some documents and start asking questions.

**Need help?** Check the full README.md for detailed documentation.
