from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from typing import Dict
import asyncio
import json
import logging
import os
import time
from uuid import uuid4
from collections import defaultdict

from app.services.rag import RAGService
from app.config import settings
from app.services.tts import TTSService
from app.services.stt import STTService
from app.services.conversation_memory import ConversationMemory

logger = logging.getLogger(__name__)
router = APIRouter()

# Initialize services
rag_service = RAGService()
tts_service = TTSService()
stt_service = STTService()
conversation_memory = ConversationMemory()

# Audio cache for session-based responses
audio_cache: Dict[str, bytes] = {}

@router.websocket("")
async def voice_websocket(websocket: WebSocket):
    session_id = f"session_{int(time.time())}_{hash(websocket) % 10000}"
    client_id = str(uuid4())
    start_time = time.time()
    
    await websocket.accept()
    logger.info(f"[{session_id}] WebSocket connected from {websocket.client} (Client ID: {client_id})")
    
    # Send ready message with session ID
    await websocket.send_text(json.dumps({
        "type": "ready",
        "session_id": session_id
    }))
    
    # Initialize conversation memory for this session
    conversation_memory.create_session(session_id)
    
    try:
        while True:
            try:
                # Receive message from client
                data = await websocket.receive_text()
                received_time = time.time()
                # logger.debug(f"[{session_id}] Received data at {received_time:.3f}s: {data[:50]}...")
                
                message_data = json.loads(data)
                
                if message_data.get("type") == "transcript":
                    transcript = message_data.get("text", "")
                    
                    if not transcript.strip():
                        continue
                        
                    logger.info(f"[{session_id}] Processing transcript: '{transcript}'")
                    
                    # Add to conversation memory
                    conversation_memory.add_interaction(
                        session_id, 
                        user_message=transcript, 
                        bot_response=""
                    )
                    
                    # Check if this query has been cached for this session
                    cache_key = f"{session_id}:{transcript.lower().strip()}"
                    
                    if cache_key in audio_cache:
                        logger.info(f"[{session_id}] Sending cached voice response")
                        # Send cached response
                        await websocket.send_text(json.dumps({
                            "type": "answer",
                            "text": audio_cache[cache_key], # Note: This seems to store text, not audio bytes based on original code usage
                            "session_id": session_id
                        }))
                        continue
                    
                    # Send transcript back to confirm receipt
                    await websocket.send_text(json.dumps({
                        "type": "transcript",
                        "text": transcript
                    }))
                    
                    # Process the query using RAG
                    process_start = time.time()
                    try:
                        # Check if Groq client is available
                        if not settings.groq_client:
                            error_msg = f"I'm having trouble connecting to the AI service. Please make sure your GROQ_API_KEY is set in the environment."
                            log_msg = "GROQ_API_KEY not set"
                            logger.error(f"[{session_id}] {log_msg}")
                            await websocket.send_text(json.dumps({
                                "type": "answer",
                                "text": error_msg,
                                "session_id": session_id
                            }))
                            continue
                        
                        # Set clients for RAG service
                        college_config = {
                            'name': settings.college_name,
                            'admissions_phone': settings.admissions_phone,
                            'support_email': settings.support_email
                        }
                        rag_service.set_clients(settings.groq_client, college_config)
                        
                        # Get response from RAG service
                        response_text = ""
                        async for result in rag_service.query_stream(transcript, session_id):
                            if result["type"] == "answer":
                                # Use the generated answer
                                response_text = result["answer"]
                                break
                            elif result["type"] == "error":
                                response_text = f"I'm having trouble processing your request: {result['message']}"
                                logger.error(f"[{session_id}] RAG Error: {result['message']}")
                                break
                        
                        # If no response from RAG, use default response
                        if not response_text:
                            response_text = "I don't have that information. Please contact Dr. B.C. Roy Engineering College Admissions at +91-343-2567890"
                        
                        logger.info(f"[{session_id}] RAG Response generated in {time.time() - process_start:.2f}s: '{response_text[:50]}...'")
                        
                        # Update conversation memory with the response
                        conversation_memory.update_last_response(session_id, response_text)
                        
                        # Generate audio if not cached
                        if cache_key not in audio_cache:
                            # Convert response to speech
                            try:
                                tts_start = time.time()
                                audio_bytes = await tts_service.text_to_speech(response_text)
                                logger.info(f"[{session_id}] TTS generated in {time.time() - tts_start:.2f}s ({len(audio_bytes)} bytes)")
                                
                                # Cache the full answer for this session (Storing text as per original logic, though variable name suggests audio?)
                                # Original code stored 'response_text' in 'audio_cache' (Dict[str, bytes] typed, but assigned str).
                                # We will conform to existing logic but note the discrepancy.
                                audio_cache[cache_key] = response_text
                                
                                # Send the answer to the client (Original code sends TEXT, not audio bytes?)
                                # Based on 'voice.py' analysis, it sends: {"type": "answer", "text": response_text}
                                # If the frontend expects audio, it is MISSING.
                                # However, I will preserve existing behavior + Logging.
                                await websocket.send_text(json.dumps({
                                    "type": "answer",
                                    "text": response_text,
                                    "session_id": session_id
                                    # "audio": base64? - Original code didn't have it.
                                }))
                                logger.info(f"[{session_id}] Response sent to client")
                                
                            except Exception as e:
                                logger.error(f"[{session_id}] TTS error: {e}")
                                
                                # Send text-only response if TTS fails
                                await websocket.send_text(json.dumps({
                                    "type": "answer",
                                    "text": response_text,
                                    "session_id": session_id
                                }))
                        else:
                            # Send cached response
                            logger.info(f"[{session_id}] Sending cached response")
                            await websocket.send_text(json.dumps({
                                "type": "answer",
                                "text": audio_cache[cache_key],
                                "session_id": session_id
                            }))
                            
                    except Exception as e:
                        logger.error(f"[{session_id}] Error processing transcript: {e}", exc_info=True)
                        error_msg = "Sorry, I encountered an error processing your request."
                        
                        await websocket.send_text(json.dumps({
                            "type": "answer",
                            "text": error_msg,
                            "session_id": session_id
                        }))
                
                elif message_data.get("type") == "interrupt":
                    # Handle interruption if needed
                    logger.info(f"[{session_id}] Interruption received")
                    # Could implement interruption logic here if needed
                
            except json.JSONDecodeError:
                logger.error(f"[{session_id}] Invalid JSON received")
                continue
            except WebSocketDisconnect:
                break
            except Exception as e:
                logger.error(f"[{session_id}] Error in websocket loop: {e}", exc_info=True)
                break
                
    except WebSocketDisconnect:
        duration = time.time() - start_time
        logger.info(f"[{session_id}] WebSocket disconnected after {duration:.2f}s")
    except Exception as e:
        logger.error(f"[{session_id}] Unexpected error in websocket: {e}", exc_info=True)
    finally:
        # Cleanup session data
        conversation_memory.delete_session(session_id)
        # Clear any cached audio for this session (optional)
        keys_to_remove = [key for key in audio_cache if key.startswith(session_id)]
        for key in keys_to_remove:
            del audio_cache[key]