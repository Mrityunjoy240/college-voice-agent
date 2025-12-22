import websocket
import json
import threading
import time
from app.config import settings
from typing import Callable, Optional


class STTService:
    """Speech-to-Text service using Speechmatics."""
    
    def __init__(self):
        self.ws_url = "wss://eu2.rt.speechmatics.com/v2"
        self.api_key = settings.speechmatics_api_key
        self.ws: Optional[websocket.WebSocketApp] = None
        self.on_transcript_callback = None
        self.on_error_callback = None
        self.connected = False
    
    def _on_open(self, ws):
        """Handle WebSocket connection opening."""
        # Send start recognition message
        start_recognition = {
            "message": "StartRecognition",
            "audio_format": {
                "type": "raw",
                "encoding": "pcm_f32le",
                "sample_rate": 16000
            },
            "transcription_config": {
                "language": "en",
                "operating_point": "enhanced"
            }
        }
        ws.send(json.dumps(start_recognition))
        self.connected = True
    
    def _on_message(self, ws, message):
        """Handle incoming WebSocket messages."""
        try:
            data = json.loads(message)
            if data.get("message") == "AddTranscript":
                # Extract transcript from results
                transcript = ""
                for result in data.get("results", []):
                    if result.get("type") == "RecognitionResult":
                        transcript += result.get("alternatives", [{}])[0].get("content", "") + " "
                
                if transcript.strip() and self.on_transcript_callback:
                    self.on_transcript_callback(transcript.strip())
        except Exception as e:
            if self.on_error_callback:
                self.on_error_callback(f"Message processing error: {str(e)}")
    
    def _on_error(self, ws, error):
        """Handle WebSocket errors."""
        self.connected = False
        error_msg = f"WebSocket error: {str(error)}"
        if self.on_error_callback:
            self.on_error_callback(error_msg)
        else:
            print(error_msg)
    
    def _on_close(self, ws, close_status_code, close_msg):
        """Handle WebSocket closing."""
        self.connected = False
    
    async def start_realtime_transcription(
        self, 
        on_transcript: Callable[[str], None],
        on_error: Optional[Callable[[str], None]] = None
    ):
        """Start real-time transcription session with Speechmatics."""
        self.on_transcript_callback = on_transcript
        self.on_error_callback = on_error
        
        # Create WebSocket connection
        headers = {
            "Authorization": f"Bearer {self.api_key}"
        }
        
        self.ws = websocket.WebSocketApp(
            f"{self.ws_url}?jwt={self.api_key}",
            header=headers,
            on_open=self._on_open,
            on_message=self._on_message,
            on_error=self._on_error,
            on_close=self._on_close
        )
        
        # Run WebSocket in a separate thread
        self.ws_thread = threading.Thread(target=self.ws.run_forever)
        self.ws_thread.daemon = True
        self.ws_thread.start()
        
        # Wait for connection
        timeout = 10
        while not self.connected and timeout > 0:
            time.sleep(0.1)
            timeout -= 0.1
        
        if not self.connected:
            raise Exception("Failed to connect to Speechmatics WebSocket")
    
    def stream_audio(self, audio_data: bytes):
        """Stream audio data to Speechmatics."""
        if self.ws and self.connected:
            # Speechmatics expects PCM f32le format
            # Convert bytes to float32 if needed
            self.ws.send(audio_data, opcode=websocket.ABNF.OPCODE_BINARY)
    
    def close(self):
        """Close the transcription session."""
        if self.ws:
            self.ws.close()
            self.connected = False
    
    async def transcribe_file(self, file_path: str) -> str:
        """Transcribe an audio file using Speechmatics (placeholder)."""
        return "File transcription with Speechmatics requires batch API implementation"