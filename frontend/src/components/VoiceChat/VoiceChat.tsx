import React, { useState, useEffect, useRef } from 'react';
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

    // Language options
    const languages = [
        { code: 'en-US', name: 'English (US)', flag: '🇺🇸' },
        { code: 'hi-IN', name: 'Hindi (India)', flag: '🇮🇳' },
        { code: 'bn-BD', name: 'Bengali (Bangladesh)', flag: '🇧🇩' },
        { code: 'bn-IN', name: 'Bengali (India)', flag: '🇮🇳' }
    ];

    const voice = useVoice({ language: selectedLanguage });
    const audioRef = useRef<HTMLAudioElement | null>(null);
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
            } else if (filteredVoices.length > 0) {
                setSelectedVoice(filteredVoices[0].name);
            }
        };

        loadVoices();
        window.speechSynthesis.onvoiceschanged = loadVoices;
    }, [selectedLanguage]);

    // Format text for natural speech
    const formatTextForSpeech = (text: string): string => {
        let formatted = text;

        // 1. Expand common college acronyms (Pronunciation Dictionary)
        const pronunciationMap: { [key: string]: string } = {
            "AI/ML": "Artificial Intelligence and Machine Learning",
            "AIML": "Artificial Intelligence and Machine Learning",
            "CSE": "Computer Science Engineering",
            "ECE": "Electronics and Communication Engineering",
            "IT": "I T",
            "B.Tech": "B Tech",
            "BTech": "B Tech",
            "M.Tech": "M Tech",
            "MTech": "M Tech",
            "MCA": "Master of Computer Applications",
            "BCA": "Bachelor of Computer Applications",
            "HOD": "Head of Department",
            "Dr.": "Doctor",
            "Prof.": "Professor",
            "Dept.": "Department",
            "Lab": "Laboratory",
            "Govt.": "Government",
            "Pvt.": "Private",
            "Ltd.": "Limited",
            "Estt.": "Establishment",
            "w.e.f": "with effect from",
            "viz.": "namely",
            "etc.": "et cetera",
            "No.": "Number",
            "BCREC": "B C R E C",
            "MAKAUT": "Mack-out",
            "WB": "West Bengal",
            "sem": "semester",
            "yr": "year",
            "mgmt": "management",
            "engg": "engineering"
        };

        const caseSensitiveKeys = new Set(["IT"]);

        // Replace acronyms (word-bounded)
        Object.entries(pronunciationMap).forEach(([acronym, replacement]) => {
            // Escape special regex chars in acronym
            const escaped = acronym.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
            const flags = caseSensitiveKeys.has(acronym) ? 'g' : 'gi';
            const regex = new RegExp(`\\b${escaped}\\b`, flags);
            formatted = formatted.replace(regex, replacement);
            
            // Handle slash cases specially if not covered (like AI/ML)
            if (acronym.includes('/')) {
                const slashRegex = new RegExp(escaped.replace('/', '\\/'), flags);
                formatted = formatted.replace(slashRegex, replacement);
            }
        });

        // Convert Indian number format (₹1,20,000) to words
        formatted = formatted.replace(/₹(\d{1,2}),(\d{2}),(\d{3})/g, (match, lakh, thousand, hundred) => {
            void match;
            const total = parseInt(lakh) * 100000 + parseInt(thousand) * 1000 + parseInt(hundred);
            return `${numberToWords(total)} rupees`;
        });

        // Convert regular currency (₹48,000)
        formatted = formatted.replace(/₹([\d,]+)/g, (match, num) => {
            void match;
            const number = parseInt(num.replace(/,/g, ''));
            return `${numberToWords(number)} rupees`;
        });

        // Convert standalone numbers with commas (1,20,000)
        formatted = formatted.replace(/\b(\d{1,2}),(\d{2}),(\d{3})\b/g, (match, lakh, thousand, hundred) => {
            void match;
            const total = parseInt(lakh) * 100000 + parseInt(thousand) * 1000 + parseInt(hundred);
            return numberToWords(total);
        });

        // Convert regular numbers with commas (48,000)
        formatted = formatted.replace(/\b([\d,]+)\b/g, (match, num) => {
            void match;
            if (num.includes(',')) {
                const number = parseInt(num.replace(/,/g, ''));
                if (number > 999) {
                    return numberToWords(number);
                }
            }
            return num;
        });

        // Convert percentages (85%)
        formatted = formatted.replace(/(\d+)%/g, (match, num) => { void match; return `${num} percent`; });

        // Convert phone numbers to be spoken digit by digit
        formatted = formatted.replace(/\b(\d{3})-(\d{4})-(\d{4})\b/g, (match, p1, p2, p3) => {
            void match;
            return `${p1.split('').join(' ')}, ${p2.split('').join(' ')}, ${p3.split('').join(' ')}`;
        });

        // Improve punctuation for natural pauses
        formatted = formatted.replace(/\. /g, '. ... ');
        formatted = formatted.replace(/\? /g, '? ... ');
        formatted = formatted.replace(/: /g, ': .. ');

        return formatted;
    };

    // Convert numbers to words
    const numberToWords = (num: number): string => {
        if (num === 0) return 'zero';

        const ones = ['', 'one', 'two', 'three', 'four', 'five', 'six', 'seven', 'eight', 'nine'];
        const tens = ['', '', 'twenty', 'thirty', 'forty', 'fifty', 'sixty', 'seventy', 'eighty', 'ninety'];
        const teens = ['ten', 'eleven', 'twelve', 'thirteen', 'fourteen', 'fifteen', 'sixteen', 'seventeen', 'eighteen', 'nineteen'];

        const convertLessThanThousand = (n: number): string => {
            if (n === 0) return '';
            if (n < 10) return ones[n];
            if (n < 20) return teens[n - 10];
            if (n < 100) return tens[Math.floor(n / 10)] + (n % 10 !== 0 ? ' ' + ones[n % 10] : '');
            return ones[Math.floor(n / 100)] + ' hundred' + (n % 100 !== 0 ? ' and ' + convertLessThanThousand(n % 100) : '');
        };

        if (num < 1000) return convertLessThanThousand(num);

        // Indian numbering system
        if (num >= 10000000) { // Crores
            const crores = Math.floor(num / 10000000);
            const remainder = num % 10000000;
            return convertLessThanThousand(crores) + ' crore' + (remainder !== 0 ? ' ' + numberToWords(remainder) : '');
        }
        if (num >= 100000) { // Lakhs
            const lakhs = Math.floor(num / 100000);
            const remainder = num % 100000;
            return convertLessThanThousand(lakhs) + ' lakh' + (remainder !== 0 ? ' ' + numberToWords(remainder) : '');
        }
        if (num >= 1000) { // Thousands
            const thousands = Math.floor(num / 1000);
            const remainder = num % 1000;
            return convertLessThanThousand(thousands) + ' thousand' + (remainder !== 0 ? ' ' + numberToWords(remainder) : '');
        }

        return convertLessThanThousand(num);
    };

    // Speak answer using Web Speech Synthesis
    const speakAnswer = async (text: string) => {
        // Cancel any ongoing speech
        stopSpeaking();

        const langPrefix = selectedLanguage.split('-')[0];

        // Use Server-Side TTS for Bengali (Murf.ai)
        if (langPrefix === 'bn') {
            try {
                setIsSpeaking(true);
                const voiceId = 'bn-IN-ishani'; // High quality Bengali voice
                
                const response = await fetch(`${API_BASE}/qa/tts`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ 
                        text: text,
                        voice_id: voiceId
                    })
                });

                if (!response.ok) throw new Error('TTS failed');

                const blob = await response.blob();
                const url = URL.createObjectURL(blob);
                const audio = new Audio(url);
                
                audio.onended = () => {
                    setIsSpeaking(false);
                    URL.revokeObjectURL(url);
                };
                audio.onerror = () => {
                    setIsSpeaking(false);
                    console.error("Audio playback error");
                };

                audioRef.current = audio;
                await audio.play();
                return; // Skip browser TTS
            } catch (e) {
                console.error("Server TTS failed, falling back to browser", e);
                // Fallback to browser TTS
            }
        }

        // Format text for natural speech
        const formattedText = formatTextForSpeech(text);

        const utterance = new SpeechSynthesisUtterance(formattedText);
        
        // Use selected voice
        const voiceObj = availableVoices.find(v => v.name === selectedVoice);
        if (voiceObj) {
            utterance.voice = voiceObj;
        }

        // Set language based on selected language
        utterance.lang = selectedLanguage;
        
        // Adjust speech parameters based on language for better quality
        if (langPrefix === 'bn') {
            // Bengali: Slower rate and slightly lower pitch for better clarity
            utterance.rate = 0.85;    // Slower for clearer pronunciation
            utterance.pitch = 0.95;    // Slightly lower pitch
            utterance.volume = 1.0;
        } else if (langPrefix === 'hi') {
            // Hindi: Good settings (user said it's good)
            utterance.rate = 0.9;
            utterance.pitch = 1.0;
            utterance.volume = 1.0;
        } else {
            // English and others
            utterance.rate = 0.9;     // Slightly slower for clarity
            utterance.pitch = 1.0;    // Natural pitch
            utterance.volume = 1.0;   // Full volume
        }

        utterance.onstart = () => setIsSpeaking(true);
        utterance.onend = () => setIsSpeaking(false);
        utterance.onerror = () => setIsSpeaking(false);

        utteranceRef.current = utterance;
        window.speechSynthesis.speak(utterance);
    };

    // Stop speaking
    const stopSpeaking = () => {
        window.speechSynthesis.cancel();
        setIsSpeaking(false);
    };

    // Handle voice recording
    useEffect(() => {
        if (voice.transcript && !isRecording) {
            // User finished speaking, send query
            handleVoiceQuery(voice.transcript);
        }
    }, [voice.transcript, isRecording]); // eslint-disable-line react-hooks/exhaustive-deps
    useEffect(() => {
        if (isSpeaking && voice.interimTranscript && voice.interimTranscript.length > 0) {
            stopSpeaking();
        }
    }, [isSpeaking, voice.interimTranscript]);
    useEffect(() => {
        if (isSpeaking && vadActive) {
            stopSpeaking();
        }
    }, [isSpeaking, vadActive]);

    const handleVoiceQuery = async (query: string) => {
        if (!query.trim()) return;

        setIsProcessing(true);
        setAnswer('');

        try {
            const response = await fetch(`${API_BASE}/qa/query`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ message: query }),
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const data = await response.json();
            const lang = (data.language as string) || detectLanguage(query);
            setSelectedLanguage(lang);
            setAnswer(data.answer);

            // Speak the answer
            speakAnswer(data.answer);
        } catch (error) {
            console.error('Query error:', error);
            const errorMsg = 'Sorry, I encountered an error processing your question.';
            setAnswer(errorMsg);
            speakAnswer(errorMsg);
        } finally {
            setIsProcessing(false);
        }
    };

    const startRecording = async () => {
        stopSpeaking();
        try {
            await voice.startListening();
            setIsRecording(true);
            setIsProcessing(false);
            setAnswer('');
            
            try {
                const stream = await navigator.mediaDevices.getUserMedia({
                    audio: {
                        echoCancellation: true,
                        noiseSuppression: true,
                        autoGainControl: true
                    }
                });
                
                micStreamRef.current = stream;
                const processed = noiseCanceller.processAudio(stream) || stream;
                // eslint-disable-next-line @typescript-eslint/no-explicit-any
                const Ctor: any = (window as any).AudioContext || (window as any).webkitAudioContext;
                const ctx: AudioContext = new Ctor();
                vadCtxRef.current = ctx;
                const src = ctx.createMediaStreamSource(processed);
                const analyser = ctx.createAnalyser();
                analyser.fftSize = 512;
                vadAnalyserRef.current = analyser;
                src.connect(analyser);
                const buf = new Float32Array(analyser.fftSize);
                if (vadTimerRef.current) {
                    clearInterval(vadTimerRef.current);
                }
                vadTimerRef.current = setInterval(() => {
                    if (!vadAnalyserRef.current) return;
                    vadAnalyserRef.current.getFloatTimeDomainData(buf);
                    let rms = 0;
                    for (let i = 0; i < buf.length; i++) {
                        rms += buf[i] * buf[i];
                    }
                    rms = Math.sqrt(rms / buf.length);
                    setVadActive(rms > 0.02);
                }, 50);
            } catch (err) {
                console.error("Error accessing microphone for VAD:", err);
                // We don't stop recording here because SpeechRecognition might still work
                // or it might be the one that failed if permissions were globally denied.
            }
        } catch (e) {
            console.error("Failed to start voice recognition:", e);
            setIsRecording(false);
        }
    };

    const stopRecording = () => {
        voice.stopListening();
        setIsRecording(false);
        setIsProcessing(true); // Start processing after recording stops
        setVadActive(false);
        if (vadTimerRef.current) {
            clearInterval(vadTimerRef.current);
            vadTimerRef.current = null;
        }
        if (vadCtxRef.current) {
            vadCtxRef.current.close();
            vadCtxRef.current = null;
        }
        if (micStreamRef.current) {
            micStreamRef.current.getTracks().forEach(track => track.stop());
            micStreamRef.current = null;
        }
        noiseCanceller.cleanup();
    };

    const handleTextQuery = async () => {
        if (!textInput.trim()) return;

        stopSpeaking(); // Stop any ongoing speech
        setIsProcessing(true);
        setAnswer('');

        try {
            const response = await fetch(`${API_BASE}/qa/query`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ message: textInput }),
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const data = await response.json();
            const lang = (data.language as string) || detectLanguage(textInput);
            setSelectedLanguage(lang);
            setAnswer(data.answer);

            // Speak the answer
            speakAnswer(data.answer);
            setTextInput(''); // Clear input
        } catch (error) {
            console.error('Query error:', error);
            const errorMsg = 'Sorry, I encountered an error processing your question.';
            setAnswer(errorMsg);
            speakAnswer(errorMsg);
        } finally {
            setIsProcessing(false);
        }
    };

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

                {/* Answer Area */}
                {answer && (
                    <Box sx={{ mt: 4, textAlign: 'left', p: 3, bgcolor: '#f0f4ff', borderRadius: 2, border: '1px solid #e0e7ff' }}>
                        <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 2 }}>
                            <Typography variant="h6" sx={{ color: '#1a237e', fontWeight: 600 }}>
                                Answer:
                            </Typography>
                            <Box>
                                {isSpeaking ? (
                                    <Button size="small" color="error" onClick={stopSpeaking}>Stop Speaking</Button>
                                ) : (
                                    <Button size="small" color="primary" onClick={() => speakAnswer(answer)}>🔊 Replay</Button>
                                )}
                            </Box>
                        </Box>
                        <Typography variant="body1" sx={{ whiteSpace: 'pre-wrap', mb: 2 }}>
                            {answer}
                        </Typography>

                        <Box sx={{ mt: 2, pt: 2, borderTop: '1px solid #e0e0e0', display: 'flex', justifyContent: 'flex-end', gap: 1 }}>
                             <Button
                                size="small"
                                variant={feedbackType === 'up' ? 'contained' : 'text'}
                                color="success"
                                onClick={() => { setFeedbackType('up'); }}
                            >
                                👍 Helpful
                            </Button>
                            <Button
                                size="small"
                                variant={feedbackType === 'down' ? 'contained' : 'text'}
                                color="error"
                                onClick={() => { setFeedbackType('down'); }}
                            >
                                👎 Not Helpful
                            </Button>
                        </Box>
                    </Box>
                )}

                {/* How to use */}
                <Box sx={{ mt: 6, p: 4, bgcolor: '#f8f9fa', borderRadius: 3, textAlign: 'left', border: '1px solid #e0e0e0' }}>
                    <Typography variant="h6" sx={{ mb: 3, fontFamily: '"Times New Roman", Times, serif', fontWeight: 'bold', color: '#333' }}>
                        How to use:
                    </Typography>
                    <Stack spacing={2}>
                        {[
                            "Click the microphone button and speak your question",
                            "Or type your question in the text box",
                            "Get instant answers with natural audio responses! 🔊",
                            "Select your preferred voice from the dropdown above"
                        ].map((step, index) => (
                            <Box key={index} sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
                                <Box sx={{
                                    width: 24,
                                    height: 24,
                                    borderRadius: '50%',
                                    bgcolor: '#e0e7ff',
                                    color: '#1a237e',
                                    display: 'flex',
                                    alignItems: 'center',
                                    justifyContent: 'center',
                                    fontWeight: 'bold',
                                    fontSize: '0.8rem',
                                    flexShrink: 0
                                }}>
                                    {index + 1}
                                </Box>
                                <Typography variant="body2" color="text.secondary">
                                    {step}
                                </Typography>
                            </Box>
                        ))}
                    </Stack>
                </Box>

            </Paper>
        </Container>
    );
};

export default VoiceChat;
