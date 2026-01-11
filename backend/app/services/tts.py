import logging
import io
import re
import os
import tempfile
import asyncio
from typing import Optional

from gtts import gTTS
import pyttsx3

class TTSAPIError(Exception):
    """Exception raised for TTS API errors"""
    pass

logger = logging.getLogger(__name__)

class TTSService:
    def __init__(self):
        """Initialize TTS service"""
        logger.info("TTS service initialized (Priarmy: gTTS, Fallback: pyttsx3)")
    
    async def text_to_speech(self, text: str) -> bytes:
        """
        Convert text to speech using gTTS with fallback to pyttsx3.
        Returns audio bytes (MP3 format preferred, or WAV if fallback).
        """
        # Strip markdown formatting first
        clean_text = self._strip_markdown(text)
        
        # Process text to expand acronyms for better pronunciation
        processed_text = self._expand_acronyms(clean_text)
        
        # Try gTTS first
        try:
            return await self._generate_gtts(processed_text)
        except Exception as e:
            logger.warning(f"gTTS failed ({e}), attempting fallback to pyttsx3...")
            return await self._generate_pyttsx3(processed_text)

    def _strip_markdown(self, text: str) -> str:
        """Remove markdown formatting"""
        text = re.sub(r'\*\*([^\*]+)\*\*', r'\1', text)
        text = re.sub(r'\*([^\*]+)\*', r'\1', text)
        text = re.sub(r'__([^_]+)__', r'\1', text)
        text = re.sub(r'_([^_]+)_', r'\1', text)
        text = re.sub(r'^[\s]*[•\-\*]\s+', '', text, flags=re.MULTILINE)
        text = re.sub(r'^#+\s+', '', text, flags=re.MULTILINE)
        text = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', text)
        text = re.sub(r'`([^`]+)`', r'\1', text)
        return text.strip()
    
    def _expand_acronyms(self, text: str) -> str:
        """Expand acronyms"""
        processed_text = text.replace('₹', 'rupees ')
        acronyms = {
            r'\bIT\b': 'I T',
            r'\bCSE\b': 'C S E',
            r'\bAIML\b': 'A I M L',
            r'\bECE\b': 'E C E',
            r'\bEE\b': 'E E',
            r'\bME\b': 'M E',
            r'\bCE\b': 'C E',
            r'\bCS\b': 'C S',
            r'\bDS\b': 'D S',
            r'\bCSD\b': 'C S D',
            r'\bBTech\b': 'B Tech',
            r'\bB\.Tech\b': 'B Tech',
            r'\bMTech\b': 'M Tech',
            r'\bM\.Tech\b': 'M Tech'
        }
        for pattern, replacement in acronyms.items():
            processed_text = re.sub(pattern, replacement, processed_text, flags=re.IGNORECASE)
        return processed_text

    async def _generate_gtts(self, text: str) -> bytes:
        """Generate using Google Text-to-Speech"""
        def _run():
            tts = gTTS(text=text, lang='en', tld='co.in', slow=False)
            buffer = io.BytesIO()
            tts.write_to_fp(buffer)
            buffer.seek(0)
            return buffer.getvalue()
            
        return await asyncio.to_thread(_run)

    async def _generate_pyttsx3(self, text: str) -> bytes:
        """Generate using local pyttsx3"""
        def _run():
            engine = pyttsx3.init()
            engine.setProperty('rate', 150)
            engine.setProperty('volume', 0.9)
            
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp:
                temp_filename = tmp.name
            
            try:
                engine.save_to_file(text, temp_filename)
                engine.runAndWait()
                
                with open(temp_filename, 'rb') as f:
                    audio_data = f.read()
                return audio_data
            finally:
                if os.path.exists(temp_filename):
                    os.unlink(temp_filename)
                    
        return await asyncio.to_thread(_run)
