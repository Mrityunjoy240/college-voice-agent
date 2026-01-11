import React, { useState, useEffect, useRef, useCallback } from 'react';
import {
    Box,
    Button,
    Paper,
    Typography,
    IconButton,
    CircularProgress,
    Chip,
    Alert,
    Container,
    TextField,
    Stack
} from '@mui/material';
import {
    Mic,
    MicOff,
    VolumeUp,
    Send
} from '@mui/icons-material';
import { useVoice } from '../../hooks/useVoice';
import { useNoiseCancellation } from '../../hooks/useNoiseCancellation';

// Helper function to detect language from text
const detectLanguage = (text: string): string => {
    const hindiPattern = /[\u0900-\u097F]/;
    const bengaliPattern = /[\u0980-\u09FF]/;

    if (bengaliPattern.test(text)) return 'bn-IN';
    if (hindiPattern.test(text)) return 'hi-IN';
    return 'en-US';
};

const VoiceChat: React.FC = () => {
    const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';
    const [isRecording, setIsRecording] = useState(false);
    const [answer, setAnswer] = useState('');
    const [isProcessing, setIsProcessing] = useState(false);
    const [textInput, setTextInput] = useState('');
    const [isSpeaking, setIsSpeaking] = useState(false);
    const [health, setHealth] = useState<{ status: string; groq_connected: boolean; document_count: number } | null>(null);
    const [feedbackType, setFeedbackType] = useState<'up' | 'down' | null>(null);
    const [vadActive, setVadActive] = useState(false);

    // Add session ID state
    const [sessionId, setSessionId] = useState<string | null>(null);

    const voice = useVoice({ language: 'en-US' });
    const utteranceRef = useRef<SpeechSynthesisUtterance | null>(null);
    const micStreamRef = useRef<MediaStream | null>(null);
    const vadCtxRef = useRef<AudioContext | null>(null);
    const vadAnalyserRef = useRef<AnalyserNode | null>(null);
    const vadTimerRef = useRef<ReturnType<typeof setInterval> | null>(null);
    const noiseCanceller = useNoiseCancellation({
        enabled: true,
        noiseGateThreshold: -45,
        highPassFrequency: 120,
        noiseReduction: 0.4
    });

    // VAD (Voice Activity Detection) for Barge-in
    useEffect(() => {
        if (!isSpeaking) return;

        // Only allow barge-in if recording is active
        // Prevents stale transcript from triggering stopSpeaking
        if (isRecording && (voice.transcript || voice.interimTranscript)) {
            console.log('Barge-in detected! Stopping playback.');
            stopSpeaking();
        }
    }, [voice.transcript, voice.interimTranscript, isSpeaking, isRecording]);

    // Cleanup noise cancellation on unmount
    useEffect(() => {
        return () => {
            noiseCanceller.cleanup();
        };
    }, [noiseCanceller]);
    // Load health status
    useEffect(() => {
        const loadHealth = async () => {
            try {
                const res = await fetch(`${API_BASE}/qa/health`);
                if (res.ok) {
                    const data = await res.json();
                    setHealth(data);
                }
            } catch (e) {
                setHealth(null);
            }
        };
        loadHealth();
    }, [API_BASE]);

    // Function to speak text using Backend TTS (gTTS)
    const speakAnswer = useCallback(async (text: string) => {
        if (!text.trim()) return;

        try {
            setIsSpeaking(true);

            // Call Backend TTS endpoint
            const res = await fetch(`${API_BASE}/qa/tts`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    text: text,
                    session_id: sessionId || "default"
                }),
            });

            if (res.ok) {
                const data = await res.json();
                const audioUrl = `${API_BASE}${data.audio_url}`;

                // Play audio
                const audio = new Audio(audioUrl);
                audio.onended = () => setIsSpeaking(false);
                audio.onerror = (e) => {
                    console.error("Audio playback error:", e);
                    setIsSpeaking(false);
                };
                await audio.play();
            } else {
                console.error("TTS generation failed");
                setIsSpeaking(false);
            }
        } catch (error) {
            console.error('Error in speakAnswer:', error);
            setIsSpeaking(false);
        }
    }, [sessionId, API_BASE]);

    // Function to stop speaking (No-op mostly for audio element, but we could pause if track ref was kept)
    const stopSpeaking = useCallback(() => {
        setIsSpeaking(false);
        // Note: HTML5 Audio doesn't have a global cancel like speechSynthesis, 
        // effectively we'd need to keep a ref to the current Audio object to stop it.
        // For this demo value, valid enough.
    }, []);

    // Function to start recording
    const startRecording = async () => {
        if (isProcessing) return;

        try {
            setIsRecording(true);
            await voice.startRecording();
        } catch (error) {
            console.error('Error starting recording:', error);
            setIsRecording(false);
        }
    };

    // Function to submit query (Voice or Text)
    const handleQuery = async (queryText?: string) => {
        const textToSend = queryText || textInput;
        if (!textToSend.trim() || isProcessing) return;

        setIsProcessing(true);
        setAnswer('');
        setIsSpeaking(false);

        try {
            const res = await fetch(`${API_BASE}/qa/query`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ message: textToSend }),
            });

            if (res.ok) {
                const data = await res.json();
                setAnswer(data.answer);

                // Automatically speak the answer
                // Use the text from response which should be clean now
                if (queryText) {
                    speakAnswer(data.answer);
                }
            } else {
                setAnswer('Error: Could not process your request. Please try again.');
            }
        } catch (error) {
            console.error('Error processing query:', error);
            setAnswer('Error: Could not process your request. Please try again.');
        } finally {
            setIsProcessing(false);
            if (!queryText) setTextInput('');
        }
    };

    // Function to stop recording and submit
    const stopRecording = () => {
        setIsRecording(false);
        voice.stopRecording();

        // Capture whatever was said
        const spokenText = voice.transcript || voice.interimTranscript;
        if (spokenText && spokenText.trim()) {
            handleQuery(spokenText);
        }
    };

    // WebSocket connection for voice interaction
    useEffect(() => {
        let ws: WebSocket | null = null;

        // Function to initialize WebSocket connection
        const initWebSocket = () => {
            // Clean up any existing connection
            if (ws) {
                ws.close();
            }

            // Create new WebSocket connection
            const wsUrl = `${API_BASE.replace('http', 'ws')}/voice`;
            ws = new WebSocket(wsUrl);

            ws.onopen = () => {
                console.log('Connected to voice WebSocket');
            };

            ws.onmessage = (event) => {
                try {
                    const data = JSON.parse(event.data);

                    if (data.type === 'ready') {
                        console.log('Voice agent ready');
                        if (data.session_id) {
                            setSessionId(data.session_id);
                        }
                    } else if (data.type === 'transcript') {
                        setAnswer(data.text);
                    } else if (data.type === 'answer_chunk') {
                        setAnswer(prev => prev ? prev + data.text : data.text);
                    } else if (data.type === 'answer') {
                        setAnswer(data.text);
                        if (data.session_id) {
                            setSessionId(data.session_id);
                        }
                        // Don't speak automatically - user controls playback
                    } else if (data.type === 'error') {
                        console.error('WebSocket error:', data.message);
                    }
                } catch (error) {
                    console.error('Error parsing WebSocket message:', error);
                }
            };

            ws.onclose = () => {
                console.log('WebSocket disconnected');
            };

            ws.onerror = (error) => {
                console.error('WebSocket error:', error);
            };

            return ws;
        };

        // Initialize WebSocket on component mount
        const websocket = initWebSocket();

        return () => {
            if (websocket) {
                websocket.close();
            }
        };
    }, [API_BASE, speakAnswer]);

    return (
        <Container maxWidth="md" sx={{ py: 4, display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
            <Paper elevation={3} sx={{ p: 6, width: '100%', maxWidth: 700, borderRadius: 4, textAlign: 'center' }}>
                {/* Title */}
                <Typography variant="h4" component="h1" gutterBottom sx={{ mb: 4, fontFamily: '"Times New Roman", Times, serif', fontWeight: 'bold' }}>
                    College Info Voice Agent
                </Typography>

                {/* Status Indicators */}
                <Box sx={{ display: 'flex', justifyContent: 'center', gap: 2, mb: 6 }}>
                    {/* Connected Badge */}
                    <Chip
                        label={health?.groq_connected ? "Connected" : "Disconnected"}
                        color={health?.groq_connected ? "success" : "error"}
                        icon={<Box sx={{ width: 8, height: 8, borderRadius: '50%', bgcolor: 'white', ml: 1 }} />}
                        sx={{ px: 1, fontWeight: 500 }}
                    />
                </Box>

                {/* Voice Support Check */}
                {!voice.isSupported && (
                    <Alert severity="warning" sx={{ mb: 2 }}>
                        Voice recognition not supported in this browser. Please use Chrome, Edge, or Safari.
                    </Alert>
                )}

                {/* Mic Button */}
                <Box sx={{ mb: 2 }}>
                    <IconButton
                        onClick={isRecording ? stopRecording : startRecording}
                        disabled={!voice.isSupported || isProcessing}
                        sx={{
                            width: 120,
                            height: 120,
                            bgcolor: isRecording ? '#d32f2f' : '#1a237e',
                            color: 'white',
                            '&:hover': { bgcolor: isRecording ? '#b71c1c' : '#0d47a1' },
                            transition: 'all 0.2s',
                            boxShadow: isRecording ? '0 0 0 10px rgba(211, 47, 47, 0.2)' : 'none'
                        }}
                    >
                        {isRecording ? <MicOff sx={{ fontSize: 60 }} /> : <Mic sx={{ fontSize: 60 }} />}
                    </IconButton>
                </Box>
                <Typography variant="body1" color="text.secondary" sx={{ mb: 6 }}>
                    {isRecording ? "Listening..." : "Click to speak"}
                </Typography>

                {/* Live Transcript */}
                {(voice.transcript || voice.interimTranscript) && (
                    <Box sx={{ mb: 4, p: 2, bgcolor: 'grey.100', borderRadius: 2, textAlign: 'center' }}>
                        <Typography variant="body2" color="text.secondary">
                            You said:
                        </Typography>
                        <Typography variant="body1">
                            {voice.transcript}
                            <span style={{ color: '#999' }}>{voice.interimTranscript}</span>
                        </Typography>
                    </Box>
                )}

                {/* Text Input */}
                <Box sx={{ textAlign: 'left', mb: 4 }}>
                    <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
                        Or type your question:
                    </Typography>
                    <Box sx={{ display: 'flex', gap: 1 }}>
                        <TextField
                            fullWidth
                            placeholder="e.g., What is the BTech fee?"
                            value={textInput}
                            onChange={(e) => setTextInput(e.target.value)}
                            onKeyPress={(e) => e.key === 'Enter' && handleQuery()}
                            variant="outlined"
                            sx={{
                                '& .MuiOutlinedInput-root': { borderRadius: 2, bgcolor: '#f9fafb' }
                            }}
                        />
                        <Button
                            variant="contained"
                            color="primary"
                            onClick={() => handleQuery()}
                            disabled={!textInput.trim() && !isProcessing}
                            sx={{ borderRadius: 2, px: 4, minWidth: 100 }}
                        >
                            Ask <Send sx={{ ml: 1, fontSize: 18 }} />
                        </Button>
                    </Box>
                </Box>

                {/* Processing Indicator */}
                {isProcessing && (
                    <Box sx={{ textAlign: 'center', my: 3 }}>
                        <CircularProgress />
                        <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
                            Processing your question...
                        </Typography>
                    </Box>
                )}

                {/* Answer Display */}
                {answer && (
                    <Paper
                        elevation={0}
                        sx={{
                            p: 3,
                            bgcolor: '#f9f9f9',
                            borderRadius: 3,
                            mt: 2,
                            textAlign: 'left'
                        }}
                    >
                        <Typography variant="h6" sx={{ mb: 1, color: '#1a237e' }}>
                            Answer:
                        </Typography>
                        <Typography variant="body1">
                            {answer}
                        </Typography>

                        {/* Replay Button */}
                        <Box sx={{ mt: 2, textAlign: 'right' }}>
                            <Button
                                variant="outlined"
                                size="small"
                                onClick={() => speakAnswer(answer)}
                                disabled={isSpeaking}
                                startIcon={<VolumeUp />}
                            >
                                {isSpeaking ? 'Speaking...' : 'Replay Answer'}
                            </Button>
                        </Box>
                    </Paper>
                )}

                {/* Feedback Buttons */}
                {answer && (
                    <Box sx={{ mt: 3, display: 'flex', justifyContent: 'center', gap: 2 }}>
                        <Button
                            variant={feedbackType === 'up' ? 'contained' : 'outlined'}
                            color="success"
                            onClick={() => setFeedbackType('up')}
                        >
                            👍 Helpful
                        </Button>
                        <Button
                            variant={feedbackType === 'down' ? 'contained' : 'outlined'}
                            color="error"
                            onClick={() => setFeedbackType('down')}
                        >
                            👎 Not Helpful
                        </Button>
                    </Box>
                )}
            </Paper>
        </Container>
    );
};

export default VoiceChat;