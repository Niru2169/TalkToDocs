"""
Text-to-Speech handler using Piper TTS
"""
import io
import wave
import numpy as np
import sounddevice as sd
import threading
import time
from pathlib import Path

class TTSHandler:
    def __init__(self, model_path: str, speed: float = 1.0):
        self.model_path = model_path
        self.speed = speed
        self.tts_engine = None
        self._initialize_tts()
    
    def _initialize_tts(self):
        """Initialize Piper TTS engine"""
        try:
            from piper.voice import PiperVoice
            
            model_path_obj = Path(self.model_path)
            
            if not model_path_obj.exists():
                print(f"❌ Model file not found: {self.model_path}")
                self.engine_type = None
                return
            
            # Check for config file
            config_path = model_path_obj.with_suffix('.onnx.json')
            if not config_path.exists():
                print(f"❌ Config file not found: {config_path}")
                self.engine_type = None
                return
            
            self.tts_engine = PiperVoice.load(self.model_path)
            self.engine_type = "piper"
            print("✅ Piper TTS initialized")
            
        except ImportError as e:
            print(f"❌ piper-tts not installed: {e}")
            print("💡 Install with: pip install piper-tts")
            self.engine_type = None
        except Exception as e:
            print(f"❌ Failed to initialize Piper TTS: {type(e).__name__}: {e}")
            self.engine_type = None
    
    def speak(self, text: str):
        """Convert text to speech and play"""
        if not text:
            return
        
        # Display the full text being spoken
        print(f"\n🔊 Speaking:\n")
        print("-" * 70)
        print(text)
        print("-" * 70)
        
        if self.engine_type == "piper":
            self._speak_piper(text)
        else:
            print("⚠️  TTS not available, text output only")
    
    def _speak_piper(self, text: str):
        """Speak using Piper"""
        try:
            # Synthesize speech using generator
            audio_generator = self.tts_engine.synthesize(text)
            
            # Collect all audio chunks
            audio_chunks = []
            sample_rate = None
            
            for chunk in audio_generator:
                # Extract audio data from AudioChunk object
                audio_data = chunk.audio_int16_array
                audio_chunks.append(audio_data)
                
                # Get sample rate from first chunk
                if sample_rate is None:
                    sample_rate = chunk.sample_rate
            
            if not audio_chunks:
                print("❌ No audio chunks generated")
                return
            
            # Concatenate all audio chunks
            audio = np.concatenate(audio_chunks)
            
            # Play audio with skip control
            self._play_audio_with_skip(audio, sample_rate)
            
        except Exception as e:
            print(f"❌ Piper TTS error: {type(e).__name__}: {e}")
    
    def _play_audio_with_skip(self, audio: np.ndarray, sample_rate: int):
        """Play audio with keyboard skip control"""
        try:
            # Import keyboard here to avoid import errors if not available
            import keyboard
            
            print("🎵 Press SPACE to skip\n")
            
            # Start audio playback
            sd.play(audio, samplerate=sample_rate)
            
            # Listen for keyboard input while playing
            while sd.get_stream().active:
                if keyboard.is_pressed('space'):
                    sd.stop()
                    print("⏭️  Skipped\n")
                    break
                
                time.sleep(0.05)  # Small delay to prevent high CPU usage
            
            # Wait for any remaining playback to finish
            sd.wait()
            
        except ImportError:
            # Fallback to simple playback if keyboard module not available
            print("⚠️  keyboard module not available. Install with: pip install keyboard")
            sd.play(audio, samplerate=sample_rate)
            sd.wait()
        except Exception as e:
            print(f"❌ Audio playback error: {e}")
            # Fallback to simple playback
            sd.play(audio, samplerate=sample_rate)
            sd.wait()