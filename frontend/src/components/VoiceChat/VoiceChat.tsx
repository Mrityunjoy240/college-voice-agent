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
    Select,
    MenuItem,
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
    const [availableVoices, setAvailableVoices] = useState<SpeechSynthesisVoice[]>([]);
    const [selectedVoice, setSelectedVoice] = useState<string>('');
    const [selectedLanguage, setSelectedLanguage] = useState<string>('en-US');
    const [health, setHealth] = useState<{ status: string; groq_connected: boolean; document_count: number } | null>(null);
    const [feedbackType, setFeedbackType] = useState<'up' | 'down' | null>(null);
    const [vadActive, setVadActive] = useState(false);
    
    // Add session ID state
    const [sessionId, setSessionId] = useState<string | null>(null);

    // Language options
    const languages = [
        { code: 'en-US', name: 'English (US)', flag: '🇺🇸' },
        { code: 'hi-IN', name: 'Hindi (India)', flag: '🇮🇳' },
        { code: 'bn-BD', name: 'Bengali (Bangladesh)', flag: '🇧🇩' },
        { code: 'bn-IN', name: 'Bengali (India)', flag: '🇮🇳' }
    ];

    const voice = useVoice({ language: selectedLanguage });
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

    // Load available voices based on selected language
    useEffect(() => {
        const loadVoices = () => {
            const voices = window.speechSynthesis.getVoices();
            
            // Get language prefix (e.g., 'en', 'hi', 'bn')
            const langPrefix = selectedLanguage.split('-')[0];
            
            // Filter voices for the selected language
            let filteredVoices = voices.filter(v => v.lang.startsWith(langPrefix));
            
            // If no voices found for the language, try to find any voice with similar language code
            if (filteredVoices.length === 0) {
                // For Bengali, try both bn-BD and bn-IN
                if (langPrefix === 'bn') {
                    filteredVoices = voices.filter(v => v.lang.includes('bn'));
                }
                // For Hindi, try hi-IN
                else if (langPrefix === 'hi') {
                    filteredVoices = voices.filter(v => v.lang.includes('hi'));
                }
            }
            
            // If still no voices, fallback to English
            if (filteredVoices.length === 0) {
                filteredVoices = voices.filter(v => v.lang.startsWith('en-'));
            }
            
            // For Bengali: Prioritize better quality voices
            if (langPrefix === 'bn' && filteredVoices.length > 0) {
                // Sort Bengali voices by quality indicators
                filteredVoices.sort((a, b) => {
                    // Prioritize voices with quality indicators
                    const aScore = 
                        (a.name.includes('Neural') || a.name.includes('Premium') || a.name.includes('Natural') ? 3 : 0) +
                        (a.name.includes('Google') || a.name.includes('Microsoft') ? 2 : 0) +
                        (a.name.includes('Female') ? 1 : 0);
                    const bScore = 
                        (b.name.includes('Neural') || b.name.includes('Premium') || b.name.includes('Natural') ? 3 : 0) +
                        (b.name.includes('Google') || b.name.includes('Microsoft') ? 2 : 0) +
                        (b.name.includes('Female') ? 1 : 0);
                    return bScore - aScore;
                });
            }
            
            // For Hindi: Prioritize better quality voices
            if (langPrefix === 'hi' && filteredVoices.length > 0) {
                filteredVoices.sort((a, b) => {
                    const aScore = 
                        (a.name.includes('Neural') || a.name.includes('Premium') || a.name.includes('Natural') ? 3 : 0) +
                        (a.name.includes('Google') || a.name.includes('Microsoft') ? 2 : 0) +
                        (a.name.includes('Female') ? 1 : 0);
                    const bScore = 
                        (b.name.includes('Neural') || b.name.includes('Premium') || b.name.includes('Natural') ? 3 : 0) +
                        (b.name.includes('Google') || b.name.includes('Microsoft') ? 2 : 0) +
                        (b.name.includes('Female') ? 1 : 0);
                    return bScore - aScore;
                });
            }
            
            setAvailableVoices(filteredVoices);
            
            // Auto-select best voice for the language
            let preferredVoice;
            
            if (langPrefix === 'bn') {
                // For Bengali, prioritize Neural, Premium, Google, Microsoft voices
                preferredVoice = 
                    filteredVoices.find(v => v.name.includes('Neural')) ||
                    filteredVoices.find(v => v.name.includes('Premium')) ||
                    filteredVoices.find(v => v.name.includes('Google')) ||
                    filteredVoices.find(v => v.name.includes('Microsoft')) ||
                    filteredVoices.find(v => v.name.includes('Natural')) ||
                    filteredVoices.find(v => v.name.includes('Female')) ||
                    filteredVoices[0];
            } else if (langPrefix === 'hi') {
                // For Hindi, similar prioritization
                preferredVoice = 
                    filteredVoices.find(v => v.name.includes('Neural')) ||
                    filteredVoices.find(v => v.name.includes('Premium')) ||
                    filteredVoices.find(v => v.name.includes('Google')) ||
                    filteredVoices.find(v => v.name.includes('Microsoft')) ||
                    filteredVoices.find(v => v.name.includes('Natural')) ||
                    filteredVoices.find(v => v.name.includes('Female')) ||
                    filteredVoices[0];
            } else {
                // For English and others
                preferredVoice = 
                    filteredVoices.find(v => v.name.includes('Natural') || v.name.includes('Premium')) ||
                    filteredVoices.find(v => v.name.includes('Female') || v.name.includes('Jenny')) ||
                    filteredVoices[0];
            }
            
            if (preferredVoice) {
                setSelectedVoice(preferredVoice.name);
            }
        };
        
        // Load voices initially
        loadVoices();
        
        // Some browsers load voices asynchronously
        window.speechSynthesis.onvoiceschanged = loadVoices;
    }, [selectedLanguage]);

    // Function to speak text
    const speakAnswer = useCallback((text: string) => {
        if (!text.trim()) return;
        
        // Cancel any ongoing speech
        if (utteranceRef.current) {
            window.speechSynthesis.cancel();
        }
        
        const utterance = new SpeechSynthesisUtterance(text);
        utteranceRef.current = utterance;
        
        // Set voice if selected
        if (selectedVoice) {
            const voice = availableVoices.find(v => v.name === selectedVoice);
            if (voice) {
                utterance.voice = voice;
            }
        }
        
        // Set language
        utterance.lang = selectedLanguage;
        
        // Set speaking state
        setIsSpeaking(true);
        
        utterance.onend = () => {
            setIsSpeaking(false);
            utteranceRef.current = null;
        };
        
        utterance.onerror = (event) => {
            console.error('Speech synthesis error:', event);
            setIsSpeaking(false);
            utteranceRef.current = null;
        };
        
        window.speechSynthesis.speak(utterance);
    }, [selectedVoice, availableVoices, selectedLanguage]);

    // Function to stop speaking
    const stopSpeaking = useCallback(() => {
        if (utteranceRef.current) {
            window.speechSynthesis.cancel();
            setIsSpeaking(false);
            utteranceRef.current = null;
        }
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

    // Function to stop recording
    const stopRecording = () => {
        setIsRecording(false);
        voice.stopRecording();
    };

    // Handle text query
    const handleTextQuery = async () => {
        if (!textInput.trim() || isProcessing) return;
        
        setIsProcessing(true);
        setAnswer('');
        
        try {
            const res = await fetch(`${API_BASE}/qa/query`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ message: textInput }),
            });
            
            if (res.ok) {
                const data = await res.json();
                setAnswer(data.answer);
            } else {
                setAnswer('Error: Could not process your request. Please try again.');
            }
        } catch (error) {
            console.error('Error processing query:', error);
            setAnswer('Error: Could not process your request. Please try again.');
        } finally {
            setIsProcessing(false);
            setTextInput('');
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
                    {/* Language Selector */}
                    <Box sx={{ display: 'flex', alignItems: 'center', bgcolor: '#f5f5f5', borderRadius: 2, px: 2 }}>
                        <VolumeUp sx={{ color: '#666', mr: 1, fontSize: 20 }} />
                        <Select
                            value={selectedLanguage}
                            onChange={(e) => {
                                setSelectedLanguage(e.target.value);
                                setSelectedVoice('');
                            }}
                            variant="standard"
                            disableUnderline
                            sx={{ fontSize: '0.9rem', color: '#333', minWidth: 100 }}
                        >
                            {languages.map((lang) => (
                                <MenuItem key={lang.code} value={lang.code}>
                                    {lang.name}
                                </MenuItem>
                            ))}
                        </Select>
                    </Box>
                    {/* Voice Selector (Optional, kept small if needed) */}
                    {availableVoices.length > 0 && (
                        <Box sx={{ display: 'flex', alignItems: 'center', bgcolor: '#f5f5f5', borderRadius: 2, px: 2 }}>
                            <Select
                                value={selectedVoice}
                                onChange={(e) => setSelectedVoice(e.target.value)}
                                variant="standard"
                                disableUnderline
                                displayEmpty
                                renderValue={(selected) => {
                                    if (!selected) return <em>Auto Voice</em>;
                                    return selected.split(' ').slice(0, 2).join(' ');
                                }}
                                sx={{ fontSize: '0.9rem', color: '#333', minWidth: 100 }}
                            >
                                <MenuItem value="">
                                    <em>Auto Select</em>
                                </MenuItem>
                                {availableVoices.map((v) => (
                                    <MenuItem key={v.name} value={v.name}>
                                        {v.name}
                                    </MenuItem>
                                ))}
                            </Select>
                        </Box>
                    )}
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
                            onKeyPress={(e) => e.key === 'Enter' && handleTextQuery()}
                            variant="outlined"
                            sx={{
                                '& .MuiOutlinedInput-root': { borderRadius: 2, bgcolor: '#f9fafb' }
                            }}
                        />
                        <Button
                            variant="contained"
                            color="primary"
                            onClick={handleTextQuery}
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