from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from typing import Dict
import asyncio
import json
import logging
import os
import time
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

@router.websocket("/voice")
async def voice_websocket(websocket: WebSocket):
    await websocket.accept()
    
    # Generate session ID
    session_id = f"session_{int(time.time())}_{hash(websocket) % 10000}"
    
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
                message_data = json.loads(data)
                
                if message_data.get("type") == "transcript":
                    transcript = message_data.get("text", "")
                    
                    if not transcript.strip():
                        continue
                    
                    # Add to conversation memory
                    conversation_memory.add_interaction(
                        session_id, 
                        user_message=transcript, 
                        bot_response=""
                    )
                    
                    # Check if this query has been cached for this session
                    cache_key = f"{session_id}:{transcript.lower().strip()}"
                    
                    if cache_key in audio_cache:
                        # Send cached response
                        await websocket.send_text(json.dumps({
                            "type": "answer",
                            "text": audio_cache[cache_key],
                            "session_id": session_id
                        }))
                        continue
                    
                    # Send transcript back to confirm receipt
                    await websocket.send_text(json.dumps({
                        "type": "transcript",
                        "text": transcript
                    }))
                    
                    # Process the query using RAG
                    try:
                        # Set clients for RAG service
                        college_config = {
                            'name': 'Dr. B.C. Roy Engineering College',
                            'admissions_phone': '+91-343-2567890',
                            'support_email': 'admissions@bcrec.ac.in'
                        }
                        rag_service.set_clients(settings.groq_client, college_config)
                        
                        # Get response from RAG service
                        response_text = ""
                        async for result in rag_service.query_stream(transcript, session_id):
                            if result["type"] == "documents" and result["documents"]:
                                # Get the best answer from retrieved documents
                                best_doc = result["documents"][0]
                                response_text = best_doc["document"]["text"][:500]  # Limit length
                                
                                # Add sentence boundary for natural pauses
                                if len(response_text) > 500:
                                    # Find a natural break point
                                    last_sentence_end = max(
                                        response_text.rfind('. ', 0, 500),
                                        response_text.rfind('? ', 0, 500),
                                        response_text.rfind('! ', 0, 500)
                                    )
                                    if last_sentence_end > 0:
                                        response_text = response_text[:last_sentence_end + 1]
                                
                                break
                            elif result["type"] == "error":
                                response_text = f"I'm having trouble processing your request: {result['message']}"
                                break
                        
                        # If no response from RAG, use default response
                        if not response_text:
                            response_text = "I don't have that information. Please contact Dr. B.C. Roy Engineering College Admissions at +91-343-2567890"
                        
                        # Update conversation memory with the response
                        conversation_memory.update_last_response(session_id, response_text)
                        
                        # Generate audio if not cached
                        if cache_key not in audio_cache:
                            # Convert response to speech
                            voice_id = settings.elevenlabs_voice_id
                            try:
                                audio_content = await tts_service.text_to_speech(response_text, voice_id)
                                
                                # Cache the full answer for this session
                                audio_cache[cache_key] = response_text
                                
                                # Send the answer to the client
                                await websocket.send_text(json.dumps({
                                    "type": "answer",
                                    "text": response_text,
                                    "session_id": session_id
                                }))
                                
                            except Exception as e:
                                logger.error(f"TTS error: {e}")
                                
                                # Send text-only response if TTS fails
                                await websocket.send_text(json.dumps({
                                    "type": "answer",
                                    "text": response_text,
                                    "session_id": session_id
                                }))
                        else:
                            # Send cached response
                            await websocket.send_text(json.dumps({
                                "type": "answer",
                                "text": audio_cache[cache_key],
                                "session_id": session_id
                            }))
                            
                    except Exception as e:
                        logger.error(f"Error processing transcript: {e}")
                        error_msg = "Sorry, I encountered an error processing your request."
                        
                        await websocket.send_text(json.dumps({
                            "type": "answer",
                            "text": error_msg,
                            "session_id": session_id
                        }))
                
                elif message_data.get("type") == "interrupt":
                    # Handle interruption if needed
                    logger.info(f"Interruption received for session {session_id}")
                    # Could implement interruption logic here if needed
                
            except json.JSONDecodeError:
                logger.error("Invalid JSON received")
                continue
            except WebSocketDisconnect:
                break
            except Exception as e:
                logger.error(f"Error in websocket loop: {e}")
                break
                
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for session {session_id}")
    except Exception as e:
        logger.error(f"Unexpected error in websocket: {e}")
    finally:
        # Cleanup session data
        conversation_memory.delete_session(session_id)
        # Clear any cached audio for this session (optional)
        keys_to_remove = [key for key in audio_cache if key.startswith(session_id)]
        for key in keys_to_remove:
            del audio_cache[key]