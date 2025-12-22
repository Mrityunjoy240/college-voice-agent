import { useState, useRef, useEffect, useCallback } from 'react';

interface UseVoiceOptions {
  language?: string;
}

interface UseVoiceReturn {
  isSupported: boolean;
  isListening: boolean;
  transcript: string;
  interimTranscript: string;
  startListening: () => Promise<void>;
  stopListening: () => void;
}

declare global {
  interface Window {
    SpeechRecognition: any;
    webkitSpeechRecognition: any;
  }
}

export const useVoice = (options: UseVoiceOptions = {}): UseVoiceReturn => {
  const [isSupported, setIsSupported] = useState(false);
  const [isListening, setIsListening] = useState(false);
  const [transcript, setTranscript] = useState('');
  const [interimTranscript, setInterimTranscript] = useState('');
  
  const recognitionRef = useRef<any>(null);
  const finalTranscriptRef = useRef('');

  useEffect(() => {
    // Check if browser supports speech recognition
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (SpeechRecognition) {
      setIsSupported(true);
      recognitionRef.current = new SpeechRecognition();
      
      // Configure recognition
      recognitionRef.current.continuous = true;
      recognitionRef.current.interimResults = true;
      recognitionRef.current.lang = options.language || 'en-US';
      
      recognitionRef.current.onresult = (event: any) => {
        let interim = '';
        for (let i = event.resultIndex; i < event.results.length; i++) {
          const transcript = event.results[i][0].transcript;
          if (event.results[i].isFinal) {
            finalTranscriptRef.current += transcript + ' ';
            setTranscript(finalTranscriptRef.current);
          } else {
            interim += transcript;
          }
        }
        setInterimTranscript(interim);
      };
      
      recognitionRef.current.onerror = (event: any) => {
        console.error('Speech recognition error', event.error);
      };
      
      recognitionRef.current.onend = () => {
        setIsListening(false);
      };
    } else {
      setIsSupported(false);
    }
    
    return () => {
      if (recognitionRef.current) {
        recognitionRef.current.stop();
      }
    };
  }, [options.language]);
  
  const startListening = useCallback(async () => {
    if (!isSupported || !recognitionRef.current) {
      throw new Error('Speech recognition not supported');
    }
    
    try {
      // Reset transcripts
      finalTranscriptRef.current = '';
      setTranscript('');
      setInterimTranscript('');
      
      // Start listening
      recognitionRef.current.start();
      setIsListening(true);
    } catch (error) {
      console.error('Error starting speech recognition:', error);
      throw error;
    }
  }, [isSupported]);
  
  const stopListening = useCallback(() => {
    if (recognitionRef.current) {
      recognitionRef.current.stop();
      setIsListening(false);
    }
  }, []);
  
  return {
    isSupported,
    isListening,
    transcript,
    interimTranscript,
    startListening,
    stopListening
  };
};