import { useState, useCallback, useEffect, useRef } from 'react';
import Webcam from 'react-webcam';
import { RingButton } from '@/components/RingButton';
import { StatusIndicator } from '@/components/StatusIndicator';
import { TranscriptDisplay } from '@/components/TranscriptDisplay';
import { useSpeechRecognition } from '@/hooks/useSpeechRecognition';
import { useAudioRecorder } from '@/hooks/useAudioRecorder';
import { ringDoorbell, getAIReply, speakText } from '@/lib/api';
import { Home, Mic, MicOff } from 'lucide-react';

type DoorbellState = 'idle' | 'ringing' | 'greeting' | 'listening' | 'processing' | 'speaking';

interface TranscriptEntry {
  role: 'visitor' | 'doorbell';
  content: string;
  timestamp: string;
}

export default function Doorbell() {
  const [state, setState] = useState<DoorbellState>('idle');
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [transcript, setTranscript] = useState<TranscriptEntry[]>([]);
  const [statusMessage, setStatusMessage] = useState<string>('');
  const [audioLevel, setAudioLevel] = useState(0);
  const [manualInput, setManualInput] = useState('');
  
  const webcamRef = useRef<Webcam>(null);

  const { 
    isListening: isBrowserListening, 
    transcript: currentSpeech, 
    startListening: startBrowserListening, 
    stopListening: stopBrowserListening, 
    resetTranscript: resetBrowserTranscript,
    isSupported,
    error: speechError
  } = useSpeechRecognition();

  const {
    isRecording,
    startRecording,
    stopRecording
  } = useAudioRecorder();

  // Simulate audio level for visual feedback
  useEffect(() => {
    if (isBrowserListening || isRecording) {
      const interval = setInterval(() => {
        setAudioLevel(Math.random() * 0.5 + 0.2);
      }, 100);
      return () => clearInterval(interval);
    }
    setAudioLevel(0);
  }, [isBrowserListening, isRecording]);

  const handleSendMessage = useCallback(async (message: string) => {
    if (!message.trim()) return;

    // Add visitor message to transcript
    const visitorEntry: TranscriptEntry = {
      role: 'visitor',
      content: message,
      timestamp: new Date().toISOString(),
    };
    setTranscript(prev => [...prev, visitorEntry]);
    setManualInput('');

    // Process with AI
    setState('processing');
    setStatusMessage('Thinking...');

    try {
      const { reply } = await getAIReply(sessionId || '', message);
      
      // Add AI response to transcript
      const doorbellEntry: TranscriptEntry = {
        role: 'doorbell',
        content: reply,
        timestamp: new Date().toISOString(),
      };
      setTranscript(prev => [...prev, doorbellEntry]);

      // Speak the reply
      setState('speaking');
      setStatusMessage('');
      await speakText(reply);

      // Go back to listening
      setState('listening');
      setStatusMessage('Speak now or type below...');
      resetBrowserTranscript();
      startBrowserListening();

    } catch (error) {
      console.error('AI reply error:', error);
      setState('idle');
      setStatusMessage('Error processing your message');
    }
  }, [sessionId, resetBrowserTranscript, startBrowserListening]);

  const handleRing = useCallback(async () => {
    setState('ringing');
    setStatusMessage('Connecting...');
    setTranscript([]);

    try {
      // Capture image from webcam if available
      let imageSrc: string | null = null;
      if (webcamRef.current) {
        imageSrc = webcamRef.current.getScreenshot();
      }

      // Ring the doorbell and get greeting (passing the image)
      const { sessionId: newSessionId, greeting } = await ringDoorbell(imageSrc);
      setSessionId(newSessionId);

      // Play greeting
      setState('greeting');
      setStatusMessage('');
      
      const doorbellEntry: TranscriptEntry = {
        role: 'doorbell',
        content: greeting,
        timestamp: new Date().toISOString(),
      };
      setTranscript([doorbellEntry]);
      
      setState('speaking');
      await speakText(greeting);

      // Start listening after greeting
      setState('listening');
      setStatusMessage('Speak now or type below...');
      resetBrowserTranscript();
      startBrowserListening();

    } catch (error) {
      console.error('Ring error:', error);
      setState('idle');
      setStatusMessage('Connection failed. Please try again.');
    }
  }, [resetBrowserTranscript, startBrowserListening]);

  const handleStopListening = useCallback(async () => {
    stopBrowserListening();
    
    if (currentSpeech.trim()) {
      handleSendMessage(currentSpeech);
    }
  }, [currentSpeech, handleSendMessage, stopBrowserListening]);

  const handleStartRecording = () => {
    stopBrowserListening();
    startRecording();
    setStatusMessage('Recording audio...');
  };

  const handleStopRecording = async () => {
    setState('processing');
    setStatusMessage('Transcribing...');
    try {
      const text = await stopRecording();
      if (text) {
        handleSendMessage(text);
      } else {
        setState('listening');
        setStatusMessage('No speech detected. Try again.');
        startBrowserListening();
      }
    } catch (error) {
      console.error('Recording error:', error);
      setState('listening');
      setStatusMessage('Recording failed. Please type.');
      startBrowserListening();
    }
  };

  const handleManualSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (manualInput.trim()) {
      stopBrowserListening();
      handleSendMessage(manualInput);
    }
  };

  // Handle end conversation
  const handleEndConversation = useCallback(() => {
    stopBrowserListening();
    setState('idle');
    setSessionId(null);
    setTranscript([]);
    setStatusMessage('');
    resetBrowserTranscript();
  }, [stopBrowserListening, resetBrowserTranscript]);

  // Map state to status for StatusIndicator
  const getStatus = () => {
    if (isRecording) return 'listening';
    switch (state) {
      case 'ringing':
      case 'processing':
        return 'processing';
      case 'listening':
        return 'listening';
      case 'greeting':
      case 'speaking':
        return 'speaking';
      default:
        return 'idle';
    }
  };

  return (
    <div className="doorbell-page min-h-screen flex flex-col items-center justify-center p-6">
      {/* Hidden Webcam for Capture */}
      <div className="absolute opacity-0 pointer-events-none">
        <Webcam
          audio={false}
          ref={webcamRef}
          screenshotFormat="image/jpeg"
          width={640}
          height={480}
        />
      </div>

      {/* Header */}
      <div className="absolute top-6 left-6 flex items-center gap-2">
        <Home className="w-5 h-5 text-doorbell-glow/60" />
        <span className="text-doorbell-glow/60 text-sm font-medium tracking-wide">
          KANDELL RESIDENCE
        </span>
      </div>

      {/* Main Content */}
      <div className="flex flex-col items-center gap-8 w-full max-w-lg">
        {/* Ring Button */}
        <div className="mb-8">
          <RingButton 
            onRing={handleRing}
            isActive={state !== 'idle'}
            disabled={state === 'processing'}
          />
        </div>

        {/* Status Indicator */}
        {state !== 'idle' && (
          <StatusIndicator 
            status={getStatus()}
            message={statusMessage}
            audioLevel={audioLevel}
          />
        )}

        {/* Transcript */}
        {transcript.length > 0 && (
          <TranscriptDisplay 
            entries={transcript}
            currentTranscript={currentSpeech}
            isListening={isBrowserListening || isRecording}
          />
        )}

        {/* Listening Controls */}
        {state === 'listening' && (
          <div className="w-full flex flex-col gap-4 mt-4">
            <div className="flex gap-3 justify-center">
              {!isRecording ? (
                <button
                  onClick={handleStartRecording}
                  className="px-6 py-3 bg-red-500/20 text-red-500 border border-red-500/30 rounded-full font-medium hover:bg-red-500/30 transition-colors flex items-center gap-2"
                >
                  <Mic className="w-4 h-4" />
                  Push to Talk
                </button>
              ) : (
                <button
                  onClick={handleStopRecording}
                  className="px-6 py-3 bg-red-500 text-white rounded-full font-medium hover:bg-red-500/90 transition-colors flex items-center gap-2 animate-pulse"
                >
                  <MicOff className="w-4 h-4" />
                  Stop & Send
                </button>
              )}
              
              <button
                onClick={handleEndConversation}
                className="px-6 py-3 bg-doorbell-surface text-doorbell-glow border border-doorbell-glow/30 rounded-full font-medium hover:bg-doorbell-glow/10 transition-colors"
              >
                End
              </button>
            </div>

            <form onSubmit={handleManualSubmit} className="flex gap-2 w-full mt-2">
              <input
                type="text"
                value={manualInput}
                onChange={(e) => setManualInput(e.target.value)}
                placeholder="Type your message..."
                className="flex-1 bg-doorbell-surface border border-doorbell-glow/30 rounded-lg px-4 py-2 text-foreground focus:outline-none focus:border-doorbell-glow/60"
              />
              <button
                type="submit"
                disabled={!manualInput.trim()}
                className="bg-doorbell-glow/20 text-doorbell-glow border border-doorbell-glow/30 rounded-lg px-4 py-2 hover:bg-doorbell-glow/30 disabled:opacity-50"
              >
                Send
              </button>
            </form>
          </div>
        )}

        {/* Speech Recognition Error Info */}
        {speechError === 'network' && state === 'listening' && (
          <p className="text-amber-500/80 text-xs text-center mt-2">
            Browser voice service unavailable. Use "Push to Talk" or type instead.
          </p>
        )}
      </div>

      {/* Footer */}
      <div className="absolute bottom-6 text-center">
        <p className="text-doorbell-glow/40 text-xs">
          Smart Doorbell System • Powered by AI
        </p>
      </div>
    </div>
  );
}
