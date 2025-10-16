"""
Configuration for Document Q&A system
"""
import os
from pathlib import Path

# Audio settings
SAMPLE_RATE = 16000
CHANNELS = 1

# Model paths and settings
SENTENCE_TRANSFORMER_MODEL = "all-MiniLM-L6-v2"
WHISPER_MODEL = "large"  # or "small", "medium", "large"
OLLAMA_MODEL = "gemma3:4b"  # Use your installed model

# FAISS settings
FAISS_INDEX_PATH = "document_index.faiss"
INDEX_METADATA_PATH = "document_index_info.json"
CHUNK_SIZE = 500  # characters per chunk
CHUNK_OVERLAP = 50

# TTS settings (Piper)
PIPER_MODEL_PATH = str(Path(__file__).parent / "en_GB-southern_english_female-low.onnx")
TTS_SPEED = 1.0

# Notes settings
NOTES_DIR = "notes"
NOTES_FORMAT = "markdown"

# Q&A Session logging
QA_LOG_FILE = "qa_session_log.txt"

# Request timeout
REQUEST_TIMEOUT = 60

# Web browsing settings
WEB_TIMEOUT = 10
WEB_USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"

