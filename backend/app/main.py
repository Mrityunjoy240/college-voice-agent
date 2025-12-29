from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api import qa, voice
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(title="College Voice Agent API", version="1.0.0")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(qa.router, prefix="/qa", tags=["qa"])
app.include_router(voice.router, prefix="/voice", tags=["voice"])

@app.get("/")
async def root():
    return {"message": "College Voice Agent API is running!"}

@app.get("/health")
async def health():
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
