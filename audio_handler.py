"""
Audio recording and transcription with Whisper
"""
import numpy as np
import sounddevice as sd
import whisper
from typing import Optional

class AudioHandler:
    def __init__(self, model_name: str = "base", sample_rate: int = 16000, channels: int = 1):
        print(f"Loading Whisper model: {model_name}")
        self.model = whisper.load_model(model_name)
        self.sample_rate = sample_rate
        self.channels = channels
        self.recording = False
        self.audio_buffer = []
        self.stream = None
        
    def audio_callback(self, indata, frames, time, status):
        """Callback for audio stream"""
        if self.recording:
            self.audio_buffer.append(indata.copy())
    
    def start_recording(self):
        """Start recording audio"""
        if self.stream is None:
            self.audio_buffer = []
            self.stream = sd.InputStream(
                samplerate=self.sample_rate,
                channels=self.channels,
                dtype='float32',
                callback=self.audio_callback
            )
            self.stream.start()
        self.recording = True
        print("🎤 Recording started...")
    
    def stop_recording(self) -> Optional[np.ndarray]:
        """Stop recording and return audio array"""
        self.recording = False
        print("⏹️  Recording stopped.")
        
        if self.stream:
            self.stream.stop()
            self.stream.close()
            self.stream = None
        
        if self.audio_buffer:
            audio = np.concatenate(self.audio_buffer, axis=0)
            if self.channels > 1:
                audio = audio[:, 0]
            return audio.flatten()
        return None
    
    def transcribe(self, audio: np.ndarray) -> str:
        """Transcribe audio to text"""
        if audio is None or len(audio) == 0:
            return ""
        
        print("🔄 Transcribing audio...")
        result = self.model.transcribe(audio, language="en", fp16=False)
        text = result["text"].strip()
        print(f"📝 Transcription: {text}")
        return text
