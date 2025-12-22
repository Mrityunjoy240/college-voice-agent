# College Info Voice Agent

Full-stack RAG voice application for college information queries using Groq API, AssemblyAI, MURF.ai, and Web Speech API.

## 🎯 Features

- **Voice Interaction**: Speak your questions using browser microphone
- **Real-time STT**: AssemblyAI real-time speech-to-text
- **RAG System**: Groq API (Llama3.1-8B) with custom BM25 document retrieval
- **TTS Response**: MURF.ai human-like voice responses
- **Admin Dashboard**: Upload and manage documents (PDF, Excel, CSV, TXT)
- **Text Fallback**: Type questions if voice is unavailable

## 🛠 Tech Stack

### Backend
- FastAPI (WebSocket + REST API)
- Groq API (Llama3.1-8B)
- Custom BM25 Document Retrieval
- AssemblyAI (Speech-to-Text)
- MURF.ai (Text-to-Speech)
- PyMuPDF, pandas (Document processing)

### Frontend
- React + TypeScript
- Material-UI 5
- Web Speech API
- Vite

## 📋 Prerequisites

- Docker & Docker Compose
- (Optional) Python 3.11+ for local development
- (Optional) Node.js 18+ for local development

## 🚀 Quick Start

### 1. Clone and Setup

```bash
cd college-agent
```

### 2. Configure API Keys

Copy the example environment file:

```bash
cp backend/.env.example backend/.env
```

Edit `backend/.env` and add your API keys:

```env
ASSEMBLYAI_API_KEY=your_actual_key_here
MURF_API_KEY=your_actual_key_here
```

**Get API Keys:**
- AssemblyAI: https://www.assemblyai.com/
- MURF.ai: https://murf.ai/

### 3. Start with Docker

```bash
docker-compose up -d
```

This will start:
- OLLAMA (port 11434)
- Chroma DB (port 8001)
- Backend API (port 8000)
- Frontend (port 5173)

### 4. Pull OLLAMA Model

```bash
docker exec -it college-ollama ollama pull llama3.2:3b
```

### 5. Access the Application

- **Voice Chat**: http://localhost:5173
- **Admin Dashboard**: http://localhost:5173/admin
- **API Docs**: http://localhost:8000/docs

## 📝 Usage

### Voice Chat
1. Click the microphone button
2. Speak your question (e.g., "What is the BTech admission fee?")
3. Get instant voice response with sources

### Admin Dashboard
1. Navigate to `/admin`
2. Upload college documents (PDF, Excel, CSV, TXT)
3. Documents are automatically processed and indexed
4. Manage uploaded files and rebuild embeddings

## 🔧 Local Development (Without Docker)

### Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Start OLLAMA separately
ollama serve

# Pull model
ollama pull llama3.2:3b

# Run backend
uvicorn app.main:app --reload
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

## 📊 API Endpoints

### Voice
- `WS /ws/voice` - Real-time voice interaction

### Q&A
- `POST /qa/query` - Text-based queries
- `GET /qa/health` - Health check

### Admin
- `POST /admin/files/` - Upload document
- `GET /admin/files/` - List files
- `DELETE /admin/files/{filename}` - Delete file
- `POST /admin/rebuild-embeddings/` - Rebuild vector DB
- `GET /admin/stats/` - System statistics

## 🎨 Voice Flow

```
User speaks → Web Speech API → Audio stream
    ↓
AssemblyAI (Real-time STT) → Transcript
    ↓
OLLAMA RAG (Llama3.2) → Answer + Sources
    ↓
MURF.ai (TTS) → Audio response → Browser plays
```

## 🔒 Privacy & Security

- OLLAMA runs locally (no data sent to external LLM services)
- Chroma vector database is local
- Audio processed in real-time (not stored)
- HTTPS WebSocket support (wss://)

## 💰 Cost Estimate (Monthly)

- OLLAMA: $0 (local)
- Chroma: $0 (local)
- AssemblyAI: ~$18 (500 mins real-time)
- MURF.ai: ~$19 (50k characters)
- **Total: ~$37/month**

## 🐛 Troubleshooting

### OLLAMA not connecting
```bash
# Check if OLLAMA is running
curl http://localhost:11434/api/tags

# Restart OLLAMA container
docker restart college-ollama
```

### Voice not working
- Ensure you're using Chrome, Edge, or Safari
- Allow microphone permissions
- Check browser console for errors

### No TTS audio
- Verify MURF API key is configured
- Check backend logs for TTS errors
- System works without TTS (text-only mode)

## ☁️ Railway Deployment

For production deployment, follow the [Railway Deployment Guide](RAILWAY_DEPLOYMENT.md).

## 📦 Project Structure

```
college-agent/
├── backend/
│   ├── app/
│   │   ├── api/          # API endpoints
│   │   ├── services/     # Core services (RAG, STT, TTS)
│   │   ├── config.py     # Configuration
│   │   └── main.py       # FastAPI app
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── components/   # React components
│   │   ├── hooks/        # Custom hooks
│   │   └── App.tsx       # Main app
│   ├── package.json
│   └── Dockerfile
└── docker-compose.yml
```

## 🤝 Contributing

Feel free to submit issues and enhancement requests!

## 📄 License

MIT License
