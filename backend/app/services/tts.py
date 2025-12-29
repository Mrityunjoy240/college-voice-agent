import logging
import io
import re

from gtts import gTTS

class TTSAPIError(Exception):
    """Exception raised for TTS API errors"""
    pass

logger = logging.getLogger(__name__)

class TTSService:
    def __init__(self):
        """Initialize TTS service using gTTS"""
        logger.info("TTS service initialized with gTTS")
    
    async def text_to_speech(self, text: str, voice_id=None) -> bytes:
        """
        Convert text to speech using gTTS (Google Text-to-Speech)
        """
        # Process text to expand acronyms for better pronunciation
        processed_text = self._expand_acronyms(text)
        
        return self._generate_gtts(processed_text)
    
    def _expand_acronyms(self, text: str) -> str:
        """
        Expand acronyms and fix symbols in text for better pronunciation
        """
        # Replace rupee symbol with word for proper pronunciation
        processed_text = text.replace('₹', 'rupees ')
        
        # Define acronyms to expand with spaces for letter-by-letter pronunciation
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

    def _generate_gtts(self, text: str) -> bytes:
        """
        Generate TTS using Google Text-to-Speech
        """
        try:
            # Create gTTS object with Indian English accent
            tts = gTTS(text=text, lang='en', tld='co.in', slow=False)
            
            # Save to bytes buffer
            buffer = io.BytesIO()
            tts.write_to_fp(buffer)
            buffer.seek(0)
            
            logger.info(f"Successfully generated TTS for text: {text[:50]}...")
            return buffer.getvalue()
        except Exception as e:
            logger.error(f"Error in gTTS generation: {e}")
            raise TTSAPIError(f"TTS generation failed: {e}")
