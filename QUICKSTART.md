# Quick Start Guide

## First-Time Setup

1. **Install Dependencies**
   ```powershell
   pip install -r requirements.txt
   ```

2. **Install and Start Ollama**
   - Download from: https://ollama.ai
   - Install and run:
   ```powershell
   ollama pull llama3.2
   ollama serve
   ```

3. **Add Documents**
   - Place your .txt, .md, or .pdf files in the `put-your-documents-here` folder

4. **Run the Application**
   ```powershell
   python main.py
   ```

4. **Try with Sample Document**
   - When prompted, select the sample document by number (usually option 1)
   - Choose text mode (option 2) for first try
   - Ask: "What is machine learning?"

## Example Queries

### Q&A Mode
- "What are the types of machine learning?"
- "Explain overfitting and underfitting"
- "What are common evaluation metrics?"
- "List the key challenges in machine learning"

### Notes Mode
Switch mode by typing: `mode notes`

Then try:
- "Create a summary of machine learning types"
- "Make notes on popular algorithms"
- "Summarize the applications section"

### Web Browsing Mode
- Enter a URL: `https://en.wikipedia.org/wiki/Machine_learning`
- Or use prefix: `web: https://example.com/article`
- Then ask questions about the web page content
- Example: "Summarize the main points" or "What is mentioned about neural networks?"

## Interface Modes

### Text Mode (Recommended for Testing)
- Simple command-line interface
- Type queries directly
- Good for testing and debugging

### Audio Mode
- Hold SPACEBAR to record
- Release to process
- Requires working microphone
- Uses Whisper for transcription

## Tips

1. **First run will be slow** - Models need to download and initialize
2. **Use text mode first** to verify everything works
3. **Add documents** to the `put-your-documents-here` folder
4. **Start with sample_document.md** to test functionality
5. **Check Ollama is running** if you get connection errors
6. **Notes are saved** in the `notes/` directory

## Troubleshooting

### "Ollama not running"
```powershell
# In a separate terminal:
ollama serve
```

### "Module not found"
```powershell
pip install -r requirements.txt
```

### Audio not working
- Try text mode first
- Check microphone permissions
- Verify sounddevice installation: `python -c "import sounddevice; print(sounddevice.query_devices())"`

## Django Integration (Future)

This codebase is structured for easy Django integration:

### Planned Structure
```
django_project/
├── manage.py
├── config/
│   ├── settings.py
│   └── urls.py
├── docqa/
│   ├── views.py
│   ├── models.py
│   ├── urls.py
│   └── services/          # Import from repurposed/
│       ├── document_processor.py
│       ├── llm_handler.py
│       ├── notes_manager.py
│       └── web_browser.py
└── templates/
    └── docqa/
        ├── index.html
        ├── query.html
        └── notes.html
```

### Key Endpoints (Planned)
- `POST /api/documents/upload` - Upload and index document
- `POST /api/query` - Ask questions
- `POST /api/web/browse` - Browse and analyze web content
- `GET /api/notes` - List notes
- `POST /api/notes` - Create note
- `WebSocket /ws/audio` - Real-time audio streaming

### Frontend (Bootstrap)
- Document upload form
- Chat-style Q&A interface
- Notes list and editor
- Voice recording button
- Real-time responses

## Next Steps

1. Add your documents to the `put-your-documents-here` folder
2. Test with sample document
3. Try your own documents (txt, md, pdf)
4. Browse and analyze web pages by entering URLs
5. Experiment with different query types
6. Create and organize notes
7. Customize models in `config.py`
