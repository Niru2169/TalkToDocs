# Document Q&A and Note Taking System

A document-based Q&A system with note-taking capabilities using FAISS, Sentence Transformers, Whisper, Ollama, and TTS.

## Features

-  **Document Processing**: Load and index documents (TXT, MD, PDF)
-  **Web Browsing**: Browse and extract content from web pages
-  **Semantic Search**: Find relevant information using FAISS and Sentence Transformers
-  **Voice Input**: Record questions using Whisper transcription
-  **AI Responses**: Generate answers using Ollama (Llama 3.2)
-  **Text-to-Speech**: Hear responses with Kokoro TTS or fallback options
-  **Note Taking**: Create and save markdown notes from document content
-  **Two Modes**: Q&A mode for questions, Notes mode for creating structured notes

## Installation

### 1. Install Dependencies

```powershell
pip install numpy sounddevice whisper sentence-transformers faiss-cpu pynput requests beautifulsoup4 lxml
```

### Optional Dependencies

```powershell
# For PDF support
pip install PyPDF2

# For Piper TTS (preferred)
pip install piper-tts

# Fallback TTS options
pip install pyttsx3
```

### 2. Install Ollama

Download and install from: https://ollama.ai

Then pull a model:
```powershell
ollama pull gemma3:1b
# OR use your installed model, e.g.:
# ollama pull gemma3:1b
```

Start Ollama:
```powershell
ollama serve
```

## Usage

### Running the Application

```powershell
python main.py
```

### Document Setup

1. Place your documents (.txt, .md, or .pdf files) in the `put-your-documents-here` folder
2. Run the application - it will automatically detect and list available documents
3. Choose a document from the list or enter a custom path

### Workflow

1. **Enter document path** when prompted (supports .txt, .md, .pdf)
2. **Choose interface**:
   - Audio mode: Hold SPACEBAR to record, release to process
   - Text mode: Type your queries directly

### Modes

- **Q&A Mode**: Ask questions about the document
- **Notes Mode**: Request structured markdown notes

Switch modes:
- Audio: Type "mode qa" or "mode notes" in text mode
- Text: Type "mode qa" or "mode notes" at the prompt

### Commands (Text Mode)

- `mode qa` - Switch to Q&A mode
- `mode notes` - Switch to notes mode
- `list` - List all saved notes
- Enter a URL (e.g., `https://example.com`) - Browse and analyze web content
- `web: <url>` or `browse: <url>` - Explicitly browse a URL
- `quit` or `exit` - Exit the application

## Architecture (Django-Ready)

The codebase is modular and ready for Django integration:

### Core Modules

```
talktodocs/
├── config.py                  # Configuration settings
├── document_processor.py      # Document loading and FAISS indexing
├── audio_handler.py           # Audio recording and Whisper transcription
├── tts_handler.py             # Text-to-speech with multiple backends
├── llm_handler.py             # Ollama LLM integration
├── notes_manager.py           # Notes saving and management
├── web_browser.py             # Web browsing and content extraction
├── put-your-documents-here/   # place your documents here to read from it
└── main.py                    # CLI application
```
```

### Django Integration Plan

Each module can become a Django service:

- `document_processor.py` → Document upload and indexing service
- `audio_handler.py` → WebSocket audio streaming
- `llm_handler.py` → API endpoint for LLM queries
- `notes_manager.py` → Notes CRUD API
- `web_browser.py` → Web scraping and content extraction service

Example Django views structure:
```python
# views.py
from repurposed.document_processor import DocumentProcessor
from repurposed.llm_handler import LLMHandler

def upload_document(request):
    # Use DocumentProcessor to index uploaded file
    pass

def query_document(request):
    # Use DocumentProcessor.search() + LLMHandler.generate_response()
    pass

def save_note(request):
    # Use NotesManager.save_note()
    pass
```

## Configuration

Edit `config.py` to customize:

```python
# Models
SENTENCE_TRANSFORMER_MODEL = "all-MiniLM-L6-v2"
WHISPER_MODEL = "base"
OLLAMA_MODEL = "llama3.2"

# Audio
SAMPLE_RATE = 16000
CHANNELS = 1

# FAISS
CHUNK_SIZE = 500
CHUNK_OVERLAP = 50

# Web browsing
WEB_TIMEOUT = 10
WEB_USER_AGENT = "Mozilla/5.0..."

# Notes
NOTES_DIR = "notes"
```

## Examples

### Q&A Mode
```
You: What are the main topics covered in this document?

Response: Based on the document, the main topics include...
```

### Notes Mode
```
You: Create a summary of the key concepts

Response:
# Key Concepts

## Concept 1
- Point 1
- Point 2

## Concept 2
...
```

### Web Browsing Mode
```
You: https://en.wikipedia.org/wiki/Artificial_intelligence

🌐 Web browsing mode activated...
✅ Extracted content from: Artificial intelligence - Wikipedia

💬 What would you like to know about this page? 
You: What is the definition of artificial intelligence?

Response: Artificial intelligence (AI) is intelligence demonstrated by machines...
```

## Troubleshooting

### Ollama Connection Error
- Ensure Ollama is running: `ollama serve`
- Check if model is installed: `ollama list`