from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.services.stt import STTService
from app.services import rag_service, tts_service
import json
import asyncio

router = APIRouter()

@router.websocket("/ws/voice")
async def voice_websocket(websocket: WebSocket):
    """
    WebSocket endpoint for real-time voice interaction.
    Flow: Audio chunks → STT → RAG → TTS → Audio response
    """
    await websocket.accept()
    stt_service = None  # Only initialize when needed
    stt_initialized = False

    try:
        # Send ready signal immediately
        await websocket.send_json({
            'type': 'ready',
            'message': "Hi! I'm Sarah, the college receptionist. How can I help you today?"
        })

        # Callback for when transcription is complete
        async def on_transcript(text: str):
            """Handle completed transcript."""
            try:
                # Send transcript back to client
                await websocket.send_json({
                    'type': 'transcript',
                    'text': text
                })

                full_answer = ""
                current_sentence = ""
                
                # Helper to send audio
                async def generate_and_send_audio(text_chunk: str):
                    if not text_chunk.strip():
                        return
                    audio_bytes = await tts_service.synthesize_async(text_chunk)
                    if audio_bytes:
                        await websocket.send_json({
                            'type': 'audio_ready',
                            'size': len(audio_bytes)
                        })
                        await websocket.send_bytes(audio_bytes)

                # Query RAG system with streaming
                async for chunk in rag_service.query_stream(text):
                    if chunk['type'] == 'error':
                        await websocket.send_json({'type': 'error', 'message': chunk['message']})
                        return
                    
                    if chunk['type'] == 'meta':
                        await websocket.send_json({
                            'type': 'answer_start',
                        })
                        continue
                    
                    if chunk['type'] == 'chunk':
                        token = chunk['text']
                        full_answer += token
                        current_sentence += token
                        
                        # Send text chunk to client
                        await websocket.send_json({
                            'type': 'answer_chunk',
                            'text': token
                        })
                        
                        # Check for sentence delimiters
                        if any(punct in token for punct in ['.', '?', '!', '\n']):
                            # If sentence is long enough, generate audio
                            if len(current_sentence.strip()) > 10:
                                sentence_to_speak = current_sentence.strip()
                                current_sentence = ""
                                await generate_and_send_audio(sentence_to_speak)
                
                # Process remaining text
                if current_sentence.strip():
                    await generate_and_send_audio(current_sentence.strip())

                # Send final answer (for consistency)
                await websocket.send_json({
                    'type': 'answer',
                    'text': full_answer,
                    'sources': []
                })

            except Exception as e:
                await websocket.send_json({
                    'type': 'error',
                    'message': f'Processing error: {str(e)}'
                })

        # Listen for messages
        while True:
            try:
                # Receive audio data or control messages
                message = await websocket.receive()

                if 'text' in message:
                    # Control message
                    data = json.loads(message['text'])

                    if data.get('type') == 'stop':
                        break
                        
                    elif data.get('type') == 'text_query':
                        # Fast path for text queries - no STT needed!
                        query_text = data.get('text', '')
                        
                        # Use the same streaming logic as voice
                        await on_transcript(query_text)
                        
                    elif data.get('type') == 'start_voice':
                        # Initialize STT only when voice is needed
                        if not stt_initialized:
                            stt_service = STTService()
                            await stt_service.start_realtime_transcription(
                                on_transcript=lambda text: asyncio.create_task(on_transcript(text))
                            )
                            stt_initialized = True

                elif 'bytes' in message:
                    # Audio data - stream to STT
                    if not stt_initialized:
                        # Initialize STT on first audio chunk
                        stt_service = STTService()
                        await stt_service.start_realtime_transcription(
                            on_transcript=lambda text: asyncio.create_task(on_transcript(text))
                        )
                        stt_initialized = True
                    
                    audio_data = message['bytes']
                    stt_service.stream_audio(audio_data)

            except WebSocketDisconnect:
                break
            except Exception as e:
                await websocket.send_json({
                    'type': 'error',
                    'message': str(e)
                })

    except Exception as e:
        print(f"WebSocket error: {str(e)}")

    finally:
        # Cleanup
        if stt_service:
            stt_service.close()
        try:
            await websocket.close()
        except:
            pass
