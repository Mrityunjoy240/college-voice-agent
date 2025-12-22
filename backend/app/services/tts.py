import requests
from app.config import settings
from typing import Optional
import asyncio

class TTSService:
    """Text-to-Speech service using MURF.ai."""
    
    def __init__(self):
        self.api_key = settings.murf_api_key
        self.voice_id = settings.murf_voice_id
        self.api_url = "https://api.murf.ai/v1/speech/generate"
    
    async def synthesize_async(self, text: str, voice_id: Optional[str] = None) -> bytes:
        """
        Async version of synthesize.
        """
        return await asyncio.to_thread(self.synthesize, text, voice_id)

    def synthesize(self, text: str, voice_id: Optional[str] = None) -> bytes:
        """
        Synthesize text to speech using MURF.ai.
        Returns audio bytes (MP3 format).
        """
        if not text.strip():
            raise ValueError("Text cannot be empty")
        
        # Use provided voice_id or default
        selected_voice = voice_id or self.voice_id
        
        # Prepare request
        headers = {
            "api-key": self.api_key,
            "Content-Type": "application/json"
        }
        
        payload = {
            "voiceId": selected_voice,
            "text": text,
            "format": "mp3",
            "sampleRate": 24000,
            "speed": 1.0,
            "pitch": 1.0
        }
        
        try:
            response = requests.post(
                self.api_url,
                headers=headers,
                json=payload,
                timeout=30
            )
            
            if response.status_code == 200:
                return response.content
            else:
                # Return error message as fallback
                error_msg = f"TTS Error: {response.status_code} - {response.text}"
                print(error_msg)
                # For development without API key, return empty bytes
                return b""
        
        except requests.exceptions.RequestException as e:
            print(f"TTS Request error: {str(e)}")
            # For development without API key, return empty bytes
            return b""
    
    def get_available_voices(self) -> list:
        """Get list of available MURF.ai voices."""
        headers = {
            "api-key": self.api_key,
        }
        
        try:
            response = requests.get(
                "https://api.murf.ai/v1/speech/voices",
                headers=headers,
                timeout=10
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                return []
        
        except requests.exceptions.RequestException:
            return []
