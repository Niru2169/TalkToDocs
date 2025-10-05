"""
Configuration for Document Q&A system
"""
import os

# Audio settings
SAMPLE_RATE = 16000
CHANNELS = 1

# Model paths and settings
SENTENCE_TRANSFORMER_MODEL = "all-MiniLM-L6-v2"
WHISPER_MODEL = "base"  # or "small", "medium", "large"
OLLAMA_MODEL = "gemma3:1b"  # Use your installed model

# FAISS settings
FAISS_INDEX_PATH = "document_index.faiss"
CHUNK_SIZE = 500  # characters per chunk
CHUNK_OVERLAP = 50

# TTS settings (Piper)
PIPER_MODEL_PATH = "en_GB-southern_english_female-low.onnx"
TTS_SPEED = 1.0

# Notes settings
NOTES_DIR = "notes"
NOTES_FORMAT = "markdown"

# Request timeout
REQUEST_TIMEOUT = 60
