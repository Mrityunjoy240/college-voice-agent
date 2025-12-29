import aiohttp
import asyncio
import base64
from typing import Optional
import logging

from app.config import settings

logger = logging.getLogger(__name__)

class STTService:
    def __init__(self):
        self.api_key = settings.speechmatics_api_key
        self.base_url = "https://asr.api.speechmatics.com/v2"
    
    async def transcribe_audio(self, audio_data: str) -> str:
        """
        Transcribe audio using Speechmatics API
        audio_data: base64 encoded audio string
        """
        if not self.api_key:
            raise ValueError("Speechmatics API key not configured")
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "audio/wav"  # Assuming WAV format
        }
        
        # Decode base64 audio data
        try:
            audio_bytes = base64.b64decode(audio_data)
        except Exception as e:
            logger.error(f"Error decoding audio data: {e}")
            raise
        
        # Prepare the request
        data = {
            "type": "json",
            "transcription_config": {
                "language": "en"
            }
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                # Send audio for transcription
                async with session.post(
                    f"{self.base_url}/transcriptions",
                    headers=headers,
                    data=audio_bytes,
                    params=data
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        transcript = result.get("transcription", "")
                        logger.info(f"Successfully transcribed audio: {transcript[:50]}...")
                        return transcript
                    else:
                        error_text = await response.text()
                        logger.error(f"STT API error {response.status}: {error_text}")
                        raise Exception(f"STT API error: {response.status} - {error_text}")
        except Exception as e:
            logger.error(f"Error in transcribe_audio: {e}")
            raise