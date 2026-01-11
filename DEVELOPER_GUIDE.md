# DEVELOPER GUIDE: COLLEGE VOICE AGENT
**Complete Technical Onboarding & Reference Manual**

---

## 📋 TABLE OF CONTENTS
1. [Welcome & Overview](#-welcome--overview)
2. [Environment Setup](#-environment-setup)
3. [Architecture Deep Dive](#-architecture-deep-dive)
4. [Codebase Navigation](#-codebase-navigation)
5. [Development Workflows](#-development-workflows)
6. [Testing & Debugging](#-testing--debugging)
7. [Common Tasks](#-common-tasks)
8. [Troubleshooting Guide](#-troubleshooting-guide)
9. [Best Practices](#-best-practices)
10. [Contributing Guidelines](#-contributing-guidelines)

---

## 👋 Welcome & Overview

### What is This Project?
The **College Voice Agent** is an AI-powered voice assistant that helps prospective students get instant, accurate answers about college admissions. Think of it as "Alexa for College Admissions" - but smarter and more accurate because it only uses verified college documents.

### Technology at a Glance
-   **Frontend:** React + TypeScript (Voice UI)
-   **Backend:** Python FastAPI (RAG Engine)
-   **AI:** Groq LLM + gTTS (Voice)
-   **Database:** FAISS (Vector) + BM25 (Keyword)

### What Makes This Special?
Unlike ChatGPT which can "hallucinate" (make up facts), our system uses **Strict RAG Grounding** - it ONLY answers from college documents. If the answer isn't in the docs, it says "I don't know."

---

## 🛠️ Environment Setup

### Prerequisites Checklist
- [ ] Python 3.9 or higher
- [ ] Node.js 16 or higher
- [ ] Git
- [ ] Code editor (VS Code recommended)
- [ ] Groq API Key (free at [groq.com](https://groq.com))
- [ ] FFmpeg (for audio processing)

### Step 1: Clone the Repository
```bash
git clone <repository-url>
cd college-agent-clean
```

### Step 2: Backend Setup (Python)

#### 2.1 Create Virtual Environment
```bash
cd backend
python -m venv venv

# Windows
.\venv\Scripts\activate

# Mac/Linux
source venv/bin/activate
```

#### 2.2 Install Dependencies
```bash
pip install -r requirements.txt
```

**Key Dependencies:**
-   `fastapi`: Web framework
-   `groq`: LLM API client
-   `sentence-transformers`: Embeddings
-   `faiss-cpu`: Vector search
-   `gtts`: Text-to-speech
-   `rank-bm25`: Keyword search

#### 2.3 Configure Environment Variables
Create a `.env` file in the `backend/` directory:
```bash
# Required
GROQ_API_KEY=your_groq_api_key_here

# Optional (defaults shown)
TEMP_AUDIO_DIR=./temp_audio
CHROMA_DB_PATH=./chroma_db
RATE_LIMIT=10/minute
CORS_ORIGINS=*
```

**Get Groq API Key:**
1. Visit [console.groq.com](https://console.groq.com)
2. Sign up (free)
3. Create API key
4. Copy to `.env` file

#### 2.4 Initialize Database
```bash
# Process documents and build indexes
python process_and_monitor.py
```

This will:
-   Read files from `uploads/`
-   Generate embeddings
-   Build FAISS and BM25 indexes
-   Save to `documents.json`

#### 2.5 Start Backend Server
```bash
# Development mode (auto-reload)
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Production mode
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

**Verify Backend:**
Open [http://localhost:8000/health](http://localhost:8000/health)

Expected response:
```json
{
  "status": "healthy",
  "groq_connected": true,
  "document_count": 487
}
```

### Step 3: Frontend Setup (React)

#### 3.1 Install Dependencies
```bash
cd frontend
npm install
```

**Key Dependencies:**
-   `react`: UI framework
-   `@mui/material`: Component library
-   `typescript`: Type safety
-   `vite`: Build tool

#### 3.2 Configure Environment
Create `.env` file in `frontend/`:
```bash
VITE_API_URL=http://localhost:8000
```

#### 3.3 Start Development Server
```bash
npm run dev
```

**Access Frontend:**
Open [http://localhost:5173](http://localhost:5173)

### Step 4: Verify Installation
Run the automated verification script:
```bash
cd backend
python verify_demo.py
```

Expected output:
```
Testing /health...
✅ Health Check Passed

Testing /qa/query (Text)...
✅ Formatting Check Passed (Clean text)
✅ Query Passed

Testing /qa/tts (Voice)...
✅ Text-to-Speech & Static Serving Passed

Summary: 3/3 Tests Passed
🚀 System is Ready for Demo!
```

---

## 🏗️ Architecture Deep Dive

### System Architecture Overview

```mermaid
graph TB
    subgraph "User Interaction"
        A[User Speaks]
        B[User Hears Response]
    end
    
    subgraph "Frontend - VoiceChat.tsx"
        C[Browser STT]
        D[Send to Backend]
        E[Receive Answer]
        F[Request TTS]
        G[Play Audio]
    end
    
    subgraph "Backend - FastAPI"
        H[/qa/query]
        I[/qa/tts]
    end
    
    subgraph "RAG Service - rag.py"
        J[Query Expansion]
        K[Hybrid Retrieval]
        L[Context Building]
        M[LLM Generation]
    end
    
    subgraph "Data Sources"
        N[FAISS Vector DB]
        O[BM25 Index]
        P[Groq LLM]
        Q[gTTS Engine]
    end
    
    A --> C
    C --> D
    D --> H
    H --> J
    J --> K
    K --> N
    K --> O
    K --> L
    L --> M
    M --> P
    P --> M
    M --> H
    H --> E
    E --> F
    F --> I
    I --> Q
    Q --> I
    I --> G
    G --> B
```

### Component Responsibilities

#### Frontend Components

**`VoiceChat.tsx` (Main UI)**
-   **Purpose:** User interface for voice interaction
-   **Key Functions:**
    -   `startRecording()`: Activates microphone
    -   `stopRecording()`: Stops recording and sends query
    -   `handleQuery()`: Sends text to backend
    -   `speakAnswer()`: Plays TTS audio
-   **State Management:**
    -   `isRecording`: Mic active state
    -   `isProcessing`: Backend processing state
    -   `isSpeaking`: Audio playback state
    -   `answer`: Current response text

**`useVoice.ts` (Speech Recognition Hook)**
-   **Purpose:** Wrapper for Web Speech API
-   **Key Features:**
    -   Real-time transcript updates
    -   Error handling
    -   Language configuration
-   **Browser Support:** Chrome, Edge, Safari

#### Backend Services

**`app/services/rag.py` (THE BRAIN)**

This is the most critical file. It contains the entire RAG logic.

**Key Classes:**

**1. HybridRetriever**
```python
class HybridRetriever:
    def __init__(self, documents, embedding_model):
        # Initializes FAISS and BM25 indexes
        
    def retrieve(self, query, top_k=5):
        # Performs hybrid search
        # Returns: List of {document, hybrid_score}
```

**How it works:**
1. Converts query to embedding (384-dim vector)
2. Searches FAISS for semantic matches
3. Searches BM25 for keyword matches
4. Combines scores: `0.6 * semantic + 0.4 * keyword`
5. Returns top-K documents

**2. QueryExpander**
```python
class QueryExpander:
    def expand(self, query):
        # Uses LLM to add synonyms
        # Example: "fee" -> "fee tuition cost annual"
```

**Why?** Users often use short queries like "fee". Expansion helps find more relevant documents.

**3. SystemPromptBuilder**
```python
class SystemPromptBuilder:
    def build_system_prompt(self, retrieved_docs):
        # Creates the instruction for the LLM
        # Enforces "Context-Only" behavior
```

**Critical Section:**
```python
system_prompt = f"""You are a helpful admissions counselor.

CRITICAL INSTRUCTIONS:
1. **STRICT GROUNDING**: Answer ONLY based on provided context.
2. **NO HALLUCINATIONS**: Do not make up facts.
3. **SPEECH OPTIMIZED**: No markdown symbols.
4. **CONCISE**: Keep answers under 3 sentences.

---CONTEXT STARTS---
{context_str}
---CONTEXT ENDS---
"""
```

**⚠️ WARNING:** Do NOT modify this prompt without approval. It's the core anti-hallucination mechanism.

**4. RAGService**
```python
class RAGService:
    async def query_stream(self, query):
        # Main orchestration method
        # Steps:
        # 1. Expand query
        # 2. Retrieve documents
        # 3. Build context
        # 4. Generate answer
        # 5. Return response
```

**`app/services/tts.py` (Voice Generation)**
```python
class TTSService:
    async def text_to_speech(self, text):
        # 1. Strip markdown
        # 2. Expand acronyms (BTech -> B Tech)
        # 3. Generate MP3 using gTTS
        # 4. Save to temp_audio/
        # 5. Return URL
```

**Why preprocess text?**
-   Markdown symbols sound robotic: "star star bold star star"
-   Acronyms sound unnatural: "B-T-E-C-H" vs "B Tech"

**`app/api/qa.py` (API Endpoints)**
```python
@router.post("/query")
async def query_endpoint(request: QueryRequest):
    # 1. Validate input
    # 2. Call RAG service
    # 3. Return JSON response
    
@router.post("/tts")
async def tts_endpoint(request: TTSRequest):
    # 1. Validate text
    # 2. Generate audio
    # 3. Return audio URL
```

---

## 📁 Codebase Navigation

### Backend File Structure
```
backend/
├── app/
│   ├── main.py                 # FastAPI app initialization
│   ├── config.py               # Settings & environment vars
│   ├── logging_config.py       # Logging setup
│   ├── limiter.py              # Rate limiting
│   │
│   ├── api/
│   │   ├── qa.py               # Query & TTS endpoints
│   │   ├── voice.py            # WebSocket endpoint
│   │   ├── admin.py            # Admin dashboard
│   │   ├── auth_routes.py      # Authentication
│   │   └── monitoring.py       # Health checks
│   │
│   ├── services/
│   │   ├── rag.py              # ⭐ RAG engine (MOST IMPORTANT)
│   │   ├── tts.py              # Text-to-speech
│   │   ├── stt.py              # Speech-to-text
│   │   └── document_processor.py  # Document ingestion
│   │
│   └── models/
│       └── schemas.py          # Pydantic models
│
├── uploads/                    # Source documents (PDFs, TXT)
├── temp_audio/                 # Generated audio files
├── chroma_db/                  # Vector database
├── documents.json              # Processed document index
├── requirements.txt            # Python dependencies
├── verify_demo.py              # Automated tests
└── .env                        # Environment variables
```

### Frontend File Structure
```
frontend/
├── src/
│   ├── App.tsx                 # Main app component
│   ├── main.tsx                # Entry point
│   │
│   ├── components/
│   │   └── VoiceChat/
│   │       └── VoiceChat.tsx   # ⭐ Main UI component
│   │
│   └── hooks/
│       ├── useVoice.ts         # Speech recognition
│       └── useNoiseCancellation.ts  # Audio preprocessing
│
├── public/                     # Static assets
├── package.json                # Node dependencies
└── .env                        # Environment variables
```

### Key Files to Know

**Must Read (Start Here):**
1. `backend/app/services/rag.py` - The brain
2. `frontend/src/components/VoiceChat/VoiceChat.tsx` - The face
3. `backend/app/api/qa.py` - The interface

**Important (Read Next):**
4. `backend/app/services/tts.py` - Voice generation
5. `backend/app/main.py` - App setup
6. `frontend/src/hooks/useVoice.ts` - Speech recognition

**Reference (As Needed):**
7. `backend/app/services/document_processor.py` - Document ingestion
8. `backend/verify_demo.py` - Testing
9. `backend/app/config.py` - Configuration

---

## 🔧 Development Workflows

### Adding New College Data

**Step 1: Prepare Documents**
-   Supported formats: PDF, TXT, MD, CSV, XLSX
-   Best format: Plain text (`.txt`) with clear headings
-   Example structure:
```
# B.Tech Admissions

## Eligibility
- 12th pass with 60% in PCM
- JEE Main score required

## Fee Structure
- Annual tuition: ₹1,20,000
- Hostel: ₹60,000
```

**Step 2: Upload Files**
```bash
# Copy files to uploads directory
cp your_document.txt backend/uploads/
```

**Step 3: Reindex**
```bash
cd backend
python process_and_monitor.py
```

This will:
-   Read new files
-   Generate embeddings
-   Update FAISS and BM25 indexes
-   Rebuild `documents.json`

**Step 4: Verify**
```bash
# Test a query related to new content
curl -X POST http://localhost:8000/qa/query \
  -H "Content-Type: application/json" \
  -d '{"message": "What is the BTech fee?"}'
```

### Modifying the Agent's Personality

**Location:** `backend/app/services/rag.py` → `SystemPromptBuilder.build_system_prompt()`

**Example: Make it more friendly**
```python
system_prompt = f"""You are a warm and friendly admissions counselor for {self.config['name']}.

Your role is to act as a **Voice Assistant** who genuinely cares about helping students.

CRITICAL INSTRUCTIONS:
1. **STRICT GROUNDING**: Answer ONLY based on provided context.
2. **NO HALLUCINATIONS**: Do not make up facts.
3. **SPEECH OPTIMIZED**: 
   - Use conversational language
   - Add warmth: "I'd be happy to help!"
   - No markdown symbols
4. **CONCISE**: Keep answers under 3 sentences unless asked for details.
...
"""
```

**⚠️ Important Rules:**
-   NEVER remove "STRICT GROUNDING" instruction
-   NEVER remove "NO HALLUCINATIONS" instruction
-   ALWAYS keep "SPEECH OPTIMIZED" (no markdown)
-   Test thoroughly after changes

### Adding a New API Endpoint

**Example: Add a "Feedback" endpoint**

**Step 1: Define Schema** (`backend/app/models/schemas.py`)
```python
class FeedbackRequest(BaseModel):
    session_id: str
    rating: int  # 1-5
    comment: Optional[str] = None
```

**Step 2: Create Endpoint** (`backend/app/api/qa.py`)
```python
@router.post("/feedback")
async def submit_feedback(request: FeedbackRequest):
    # Save feedback to database/file
    logger.info(f"Feedback: {request.rating}/5 - {request.comment}")
    return {"status": "success"}
```

**Step 3: Update Frontend** (`VoiceChat.tsx`)
```typescript
const submitFeedback = async (rating: number) => {
    await fetch(`${API_BASE}/qa/feedback`, {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({
            session_id: sessionId,
            rating: rating
        })
    });
};
```

---

## 🧪 Testing & Debugging

### Running Tests

**Automated Test Suite:**
```bash
cd backend
python verify_demo.py
```

**What it tests:**
1. **Health Check:** Is the server running?
2. **Query Processing:** Can it answer questions?
3. **Formatting:** Are there markdown symbols in output?
4. **TTS Generation:** Is audio being created?
5. **Static Serving:** Can frontend access audio files?

**Manual Testing:**

**Test 1: Text Query**
```bash
curl -X POST http://localhost:8000/qa/query \
  -H "Content-Type: application/json" \
  -d '{"message": "What is the BTech fee?"}'
```

**Test 2: TTS Generation**
```bash
curl -X POST http://localhost:8000/qa/tts \
  -H "Content-Type: application/json" \
  -d '{"text": "Hello, this is a test."}'
```

**Test 3: Voice Interaction**
1. Open frontend: http://localhost:5173
2. Click microphone button
3. Say: "What is the BTech fee?"
4. Verify: You hear a response in Indian accent

### Debugging Common Issues

**Issue: "Asterisks in Voice Output"**

**Symptom:** Agent says "star star bold star star" instead of reading text naturally.

**Root Cause:** LLM is outputting markdown formatting.

**Fix:**
1. Check `rag.py` → `SystemPromptBuilder`
2. Ensure "SPEECH OPTIMIZED" instruction is present
3. Run `verify_demo.py` to check for markdown leakage

**Issue: "I don't know" for Known Information**

**Symptom:** Agent says it doesn't have information that's clearly in documents.

**Root Cause:** Poor retrieval or query mismatch.

**Debug Steps:**
```python
# Add logging to rag.py
logger.info(f"Retrieved docs: {[d['document']['source'] for d in retrieved_docs]}")
logger.info(f"Hybrid scores: {[d['hybrid_score'] for d in retrieved_docs]}")
```

**Possible Fixes:**
-   Improve document formatting (clearer headings)
-   Adjust hybrid weights (currently 0.6 semantic, 0.4 keyword)
-   Add query expansion examples

**Issue: "Slow Response Time"**

**Symptom:** Takes >3 seconds to respond.

**Debug Steps:**
1. Check Groq API latency (should be <500ms)
2. Check retrieval time (should be <200ms)
3. Check TTS generation (should be <400ms)

**Add timing logs:**
```python
import time
start = time.time()
# ... code ...
logger.info(f"Operation took {time.time() - start:.2f}s")
```

**Possible Fixes:**
-   Reduce `top_k` in retrieval (currently 5)
-   Enable caching for common queries
-   Optimize embedding model (use smaller model)

---

## 📝 Common Tasks

### Task 1: Change Voice Accent

**Current:** Indian English (`co.in`)

**To change to US English:**

**File:** `backend/app/services/tts.py`
```python
# Change this line:
tts = gTTS(text=processed_text, lang='en', tld='co.in')

# To:
tts = gTTS(text=processed_text, lang='en', tld='com')
```

**Other accents:**
-   UK: `tld='co.uk'`
-   Australia: `tld='com.au'`
-   Canada: `tld='ca'`

### Task 2: Adjust Response Length

**Current:** Answers are kept under 3 sentences.

**To make longer:**

**File:** `backend/app/services/rag.py`
```python
# In SystemPromptBuilder:
# Change:
4. **CONCISE**: Keep answers under 3 sentences unless asked for details.

# To:
4. **DETAILED**: Provide comprehensive answers with all relevant details.
```

**Also adjust LLM max_tokens:**
```python
# In RAGService.query_stream():
response = self.llm.chat.completions.create(
    messages=messages,
    model="llama-3.1-8b-instant",
    temperature=0.0,
    max_tokens=150  # Increase to 300 for longer answers
)
```

### Task 3: Add Caching for Common Queries

**File:** `backend/app/api/qa.py`

```python
from functools import lru_cache

# Simple in-memory cache
query_cache = {}

@router.post("/query")
async def query_endpoint(request: QueryRequest):
    # Check cache
    cache_key = request.message.lower().strip()
    if cache_key in query_cache:
        logger.info(f"Cache hit for: {cache_key}")
        return query_cache[cache_key]
    
    # Process query
    answer = await rag_service.query_stream(request.message)
    
    # Store in cache
    response = QueryResponse(answer=answer, ...)
    query_cache[cache_key] = response
    
    return response
```

### Task 4: Export Conversation Logs

**Add logging to track all interactions:**

**File:** `backend/app/api/qa.py`
```python
import json
from datetime import datetime

@router.post("/query")
async def query_endpoint(request: QueryRequest):
    # ... existing code ...
    
    # Log interaction
    log_entry = {
        "timestamp": datetime.now().isoformat(),
        "query": request.message,
        "answer": answer,
        "session_id": session_id
    }
    
    with open("logs/conversations.jsonl", "a") as f:
        f.write(json.dumps(log_entry) + "\n")
    
    return response
```

---

## 🐛 Troubleshooting Guide

### Backend Won't Start

**Error:** `ModuleNotFoundError: No module named 'app'`

**Solution:**
```bash
# Make sure you're in the backend directory
cd backend

# Activate virtual environment
source venv/bin/activate  # Mac/Linux
.\venv\Scripts\activate   # Windows

# Run from backend directory
python -m uvicorn app.main:app --reload
```

**Error:** `groq.APIError: Invalid API key`

**Solution:**
1. Check `.env` file exists in `backend/`
2. Verify `GROQ_API_KEY=...` is set
3. Get new key from [console.groq.com](https://console.groq.com)

### Frontend Won't Connect to Backend

**Error:** `Network Error` or `CORS Error`

**Solution:**
1. Verify backend is running: http://localhost:8000/health
2. Check `frontend/.env` has correct URL:
   ```bash
   VITE_API_URL=http://localhost:8000
   ```
3. Restart frontend:
   ```bash
   npm run dev
   ```

### Voice Not Working

**Error:** "Voice recognition not supported"

**Solution:**
-   Use Chrome, Edge, or Safari (Firefox not supported)
-   Ensure HTTPS (or localhost)
-   Grant microphone permissions

**Error:** "No audio playback"

**Solution:**
1. Check browser console for errors
2. Verify audio file exists:
   ```bash
   ls backend/temp_audio/
   ```
3. Test direct URL: http://localhost:8000/audio/tts_xxx.mp3
4. Check `main.py` has static mount:
   ```python
   app.mount("/audio", StaticFiles(directory="temp_audio"), name="audio")
   ```

---

## ✅ Best Practices

### Code Quality

**1. Always Use Type Hints (Python)**
```python
# Good
def process_query(query: str, top_k: int = 5) -> List[Dict]:
    ...

# Bad
def process_query(query, top_k=5):
    ...
```

**2. Use TypeScript (Frontend)**
```typescript
// Good
const handleQuery = async (text: string): Promise<void> => {
    ...
}

// Bad
const handleQuery = async (text) => {
    ...
}
```

**3. Add Logging**
```python
# Always log important events
logger.info(f"Processing query: {query}")
logger.warning(f"No documents found for: {query}")
logger.error(f"LLM API failed: {error}")
```

### RAG Best Practices

**1. Never Modify System Prompt Without Testing**
-   Always run `verify_demo.py` after changes
-   Test with edge cases
-   Check for markdown leakage

**2. Keep Documents Clean**
-   Use clear headings
-   Avoid excessive formatting
-   Keep sentences simple

**3. Monitor Retrieval Quality**
-   Log retrieved document sources
-   Check hybrid scores
-   Adjust weights if needed

### Security Best Practices

**1. Never Commit API Keys**
```bash
# Add to .gitignore
.env
*.env
```

**2. Validate All Inputs**
```python
class QueryRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=500)
```

**3. Use Rate Limiting**
```python
# Already implemented in qa.py
@limiter.limit("10/minute")
async def query_endpoint(...):
    ...
```

---

## 🤝 Contributing Guidelines

### Git Workflow

**1. Create Feature Branch**
```bash
git checkout -b feature/add-multilingual-support
```

**2. Make Changes**
-   Write clean, documented code
-   Add tests if applicable
-   Update documentation

**3. Test Thoroughly**
```bash
# Run verification
python backend/verify_demo.py

# Test manually
# - Voice interaction
# - Text queries
# - Edge cases
```

**4. Commit with Descriptive Messages**
```bash
git commit -m "feat: Add Hindi language support for TTS

- Updated tts.py to support 'hi' language code
- Added language selector in VoiceChat.tsx
- Tested with Hindi queries"
```

**5. Push and Create Pull Request**
```bash
git push origin feature/add-multilingual-support
```

### Code Review Checklist

**Before Submitting PR:**
- [ ] All tests pass (`verify_demo.py`)
- [ ] No console errors in frontend
- [ ] Code follows existing style
- [ ] Documentation updated
- [ ] No API keys in code
- [ ] Tested on Chrome and Edge

**Critical Files (Require Extra Review):**
- [ ] `backend/app/services/rag.py` (RAG logic)
- [ ] System prompt changes
- [ ] API endpoint modifications

---

## 📚 Additional Resources

### Learning Resources

**RAG & LLMs:**
-   [RAG Explained](https://www.pinecone.io/learn/retrieval-augmented-generation/)
-   [Groq Documentation](https://console.groq.com/docs)
-   [FAISS Tutorial](https://github.com/facebookresearch/faiss/wiki)

**FastAPI:**
-   [Official Docs](https://fastapi.tiangolo.com/)
-   [Tutorial](https://fastapi.tiangolo.com/tutorial/)

**React + TypeScript:**
-   [React Docs](https://react.dev/)
-   [TypeScript Handbook](https://www.typescriptlang.org/docs/)

### Useful Commands

**Backend:**
```bash
# Start server
python -m uvicorn app.main:app --reload

# Run tests
python verify_demo.py

# Reindex documents
python process_and_monitor.py

# Check logs
tail -f logs/app.log
```

**Frontend:**
```bash
# Start dev server
npm run dev

# Build for production
npm run build

# Preview production build
npm run preview
```

---

## 🆘 Getting Help

**Found a Bug?**
1. Check this guide first
2. Search existing issues
3. Create detailed bug report with:
   -   Steps to reproduce
   -   Expected vs actual behavior
   -   Error messages
   -   System info

**Have Questions?**
-   Check PROJECT_REPORT.md for architecture details
-   Review code comments
-   Ask the team

---

**Happy Coding! 🚀**

*Last Updated: December 31, 2025*
