import { useState, useRef, useCallback } from 'react';
import { sendSpeechToText } from '@/lib/api';

export function useAudioRecorder() {
  const [isRecording, setIsRecording] = useState(false);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);

  const startRecording = useCallback(() => {
    navigator.mediaDevices.getUserMedia({ audio: true })
      .then(stream => {
        const mediaRecorder = new MediaRecorder(stream);
        mediaRecorderRef.current = mediaRecorder;
        audioChunksRef.current = [];

        mediaRecorder.ondataavailable = (event) => {
          if (event.data.size > 0) {
            audioChunksRef.current.push(event.data);
          }
        };

        mediaRecorder.start();
        setIsRecording(true);
      })
      .catch(err => {
        console.error("Error accessing microphone:", err);
      });
  }, []);

  const stopRecording = useCallback((): Promise<string> => {
    return new Promise((resolve, reject) => {
      if (!mediaRecorderRef.current) {
        reject("No media recorder found");
        return;
      }

      mediaRecorderRef.current.onstop = async () => {
        const audioBlob = new Blob(audioChunksRef.current, { type: 'audio/webm' });
        try {
          const { text } = await sendSpeechToText(audioBlob);
          resolve(text);
        } catch (error) {
          reject(error);
        } finally {
          setIsRecording(false);
          // Stop all tracks to release the microphone
          mediaRecorderRef.current?.stream.getTracks().forEach(track => track.stop());
        }
      };

      mediaRecorderRef.current.stop();
    });
  }, []);

  return {
    isRecording,
    startRecording,
    stopRecording
  };
}