#!/usr/bin/env python3
"""
CLI Application for Document Q&A and Note Taking
"""
import os
import sys
import json
import hashlib
from pathlib import Path

from config import *
from document_processor import DocumentProcessor
from audio_handler import AudioHandler
from tts_handler import TTSHandler
from llm_handler import LLMHandler
from notes_manager import NotesManager
from web_browser import WebBrowser

# Import pynput only when needed for audio mode
try:
    from pynput.keyboard import Key, Listener
    PYNPUT_AVAILABLE = True
except ImportError:
    PYNPUT_AVAILABLE = False
    print("⚠️  pynput not available. Audio mode will be disabled.")

class DocQAApp:
    def __init__(self):
        self.doc_processor = None
        self.audio_handler = None
        self.tts_handler = None
        self.llm_handler = None
        self.notes_manager = None
        self.web_browser = None
        self.recording = False
        self.mode = "qa"  # "qa" or "notes"
        self.use_tts = True  # Whether to use TTS for responses
    
    def get_file_hash(self, file_paths):
        """Generate a hash for the given file(s) to track what was indexed"""
        if isinstance(file_paths, str):
            file_paths = [file_paths]
        
        # Sort paths for consistent hashing
        sorted_paths = sorted(file_paths)
        combined = "|".join(sorted_paths)
        return hashlib.md5(combined.encode()).hexdigest()
    
    def save_index_metadata(self, file_paths):
        """Save metadata about what was indexed"""
        if isinstance(file_paths, str):
            file_paths = [file_paths]
        
        metadata = {
            "files": file_paths,
            "file_hash": self.get_file_hash(file_paths)
        }
        
        with open(INDEX_METADATA_PATH, 'w') as f:
            json.dump(metadata, f, indent=2)
    
    def load_index_metadata(self):
        """Load metadata about what was indexed"""
        if not os.path.exists(INDEX_METADATA_PATH):
            return None
        
        try:
            with open(INDEX_METADATA_PATH, 'r') as f:
                return json.load(f)
        except:
            return None
    
    def needs_reindex(self, file_paths):
        """Check if documents need to be re-indexed"""
        metadata = self.load_index_metadata()
        if not metadata:
            return True
        
        current_hash = self.get_file_hash(file_paths)
        return metadata.get("file_hash") != current_hash
        
    def initialize(self):
        """Initialize all components"""
        print("=" * 60)
        print("📚 Document Q&A System - Initializing...")
        print("=" * 60)
        
        # Initialize document processor
        print("\n🔧 Loading Sentence Transformer...")
        self.doc_processor = DocumentProcessor(
            SENTENCE_TRANSFORMER_MODEL,
            CHUNK_SIZE,
            CHUNK_OVERLAP
        )
        
        # Initialize audio handler
        print("\n🎤 Loading Whisper model...")
        self.audio_handler = AudioHandler(WHISPER_MODEL, SAMPLE_RATE, CHANNELS)
        
        # Initialize TTS
        print("\n🔊 Initializing TTS...")
        self.tts_handler = TTSHandler(PIPER_MODEL_PATH, TTS_SPEED)
        
        # Initialize LLM
        print("\n🤖 Connecting to Ollama...")
        self.llm_handler = LLMHandler(OLLAMA_MODEL)
        if self.llm_handler.check_connection():
            print(f"✅ Connected to Ollama ({OLLAMA_MODEL})")
        else:
            print("❌ Ollama is not running or not accessible.")
            print("💡 Please start Ollama with: ollama serve")
            print("💡 Then pull the model with: ollama pull", OLLAMA_MODEL)
            return False  # Return False to indicate initialization failed
        
        # Initialize notes manager
        self.notes_manager = NotesManager(NOTES_DIR)
        
        # Initialize web browser
        print("\n🌐 Initializing web browser...")
        self.web_browser = WebBrowser(WEB_TIMEOUT, WEB_USER_AGENT)
        print("✅ Web browser ready")
        
        print("\n✅ Initialization complete!")
        return True
    
    def load_documents(self, file_paths):
        """Load and index document(s)"""
        if isinstance(file_paths, str):
            file_paths = [file_paths]
        
        print(f"\n📄 Loading {len(file_paths)} document(s)...")
        for fp in file_paths:
            print(f"  - {Path(fp).name}")
        
        # Check if we can reuse existing index
        if os.path.exists(FAISS_INDEX_PATH) and not self.needs_reindex(file_paths):
            print("\n✅ Found existing index for these documents.")
            if self.doc_processor.load_index(FAISS_INDEX_PATH):
                print("✅ Index loaded successfully!")
                return True
        
        # Need to re-index
        if os.path.exists(FAISS_INDEX_PATH):
            print("\n⚠️  Different documents detected. Re-indexing...")
        
        # Index all documents
        for i, file_path in enumerate(file_paths, 1):
            print(f"\n[{i}/{len(file_paths)}] Indexing: {Path(file_path).name}")
            if i == 1:
                self.doc_processor.index_document(file_path)
            else:
                # For subsequent docs, we need to append to existing index
                self.doc_processor.index_document(file_path)
        
        # Check if indexing was successful
        if self.doc_processor.index is None or self.doc_processor.index.ntotal == 0:
            print("❌ Failed to index documents. Please check the files and try again.")
            return False
        
        # Save the index and metadata
        self.doc_processor.save_index(FAISS_INDEX_PATH)
        self.save_index_metadata(file_paths)
        
        print("\n✅ Documents loaded and indexed!")
        return True
    
    def process_query(self, query: str):
        """Process user query and generate response"""
        if not query:
            return
        
        # Check if query is a URL
        if self.web_browser.is_valid_url(query):
            self.process_web_query(query)
            return
        
        # Check if query starts with "web:" or "browse:"
        if query.lower().startswith("web:") or query.lower().startswith("browse:"):
            url = query.split(":", 1)[1].strip()
            if self.web_browser.is_valid_url(url):
                self.process_web_query(url)
            else:
                print(f"❌ Invalid URL: {url}")
            return
        
        print(f"\n🔍 Searching document...")
        
        # Search for relevant context
        results = self.doc_processor.search(query, top_k=3)
        
        if not results:
            response = "I couldn't find relevant information in the document."
            print(f"\n💬 Response: {response}")
            if self.use_tts:
                self.tts_handler.speak(response)
            return
        
        # Combine context
        context = "\n\n".join([chunk for chunk, dist, meta in results])
        
        print(f"📝 Found {len(results)} relevant chunks")
        print(f"🤔 Generating response...")
        
        # Generate response
        response = self.llm_handler.generate_response(context, query, mode=self.mode)
        
        print(f"\n{'📋' if self.mode == 'notes' else '💬'} Response:\n")
        print("-" * 60)
        print(response)
        print("-" * 60)
        
        # Save notes if in notes mode
        if self.mode == "notes":
            save = input("\n💾 Save this note? (y/n): ").strip().lower()
            if save == 'y':
                title = input("Note title (or press Enter for auto): ").strip()
                self.notes_manager.save_note(response, title or None)
        
        # Speak response
        if self.use_tts:
            self.tts_handler.speak(response)
    
    def process_web_query(self, url: str):
        """Process web URL query"""
        print(f"\n🌐 Web browsing mode activated...")
        
        # Fetch and extract web content
        web_data = self.web_browser.browse(url)
        
        if not web_data:
            response = "I couldn't fetch or extract content from the URL."
            print(f"\n💬 Response: {response}")
            if self.use_tts:
                self.tts_handler.speak(response)
            return
        
        # Create a temporary index for web content
        print(f"\n📄 Indexing web content from: {web_data['title']}")
        
        # Save current index state
        original_chunks = self.doc_processor.chunks
        original_metadata = self.doc_processor.metadata
        original_index = self.doc_processor.index
        
        # Create chunks from web content
        self.doc_processor.chunks = self.doc_processor.chunk_text(web_data['text'])
        self.doc_processor.metadata = [{
            "source": url,
            "title": web_data['title'],
            "chunk_id": i
        } for i in range(len(self.doc_processor.chunks))]
        
        # Generate embeddings for web content
        print("Generating embeddings for web content...")
        embeddings = self.doc_processor.model.encode(self.doc_processor.chunks, show_progress_bar=True)
        
        if embeddings.ndim == 1:
            embeddings = embeddings.reshape(1, -1)
        
        # Create temporary index
        dimension = embeddings.shape[1]
        import faiss
        temp_index = faiss.IndexFlatL2(dimension)
        temp_index.add(embeddings.astype('float32'))
        self.doc_processor.index = temp_index
        
        print(f"✅ Web content indexed: {temp_index.ntotal} chunks")
        
        # Ask user what they want to know about the web page
        print("\n" + "=" * 60)
        print(f"📄 Page Title: {web_data['title']}")
        if web_data['description']:
            print(f"📝 Description: {web_data['description'][:200]}...")
        print("=" * 60)
        
        web_query = input("\n💬 What would you like to know about this page? (or press Enter for summary): ").strip()
        
        if not web_query:
            web_query = "Summarize the main content of this page"
        
        # Search web content
        results = self.doc_processor.search(web_query, top_k=3)
        
        if results:
            context = "\n\n".join([chunk for chunk, dist, meta in results])
            print(f"\n🤔 Generating response based on web content...")
            
            # Generate response
            response = self.llm_handler.generate_response(context, web_query, mode=self.mode)
            
            print(f"\n{'📋' if self.mode == 'notes' else '💬'} Response:\n")
            print("-" * 60)
            print(response)
            print("-" * 60)
            
            # Save notes if requested
            if self.mode == "notes":
                save = input("\n💾 Save this note? (y/n): ").strip().lower()
                if save == 'y':
                    title = input("Note title (or press Enter for auto): ").strip()
                    if not title:
                        title = web_data['title']
                    self.notes_manager.save_note(response, title)
            
            # Speak response
            if self.use_tts:
                self.tts_handler.speak(response)
        else:
            print("\n❌ Couldn't extract information from web content")
        
        # Restore original index
        self.doc_processor.chunks = original_chunks
        self.doc_processor.metadata = original_metadata
        self.doc_processor.index = original_index
        print("\n✅ Restored original document index")
    
    def on_press(self, key):
        """Handle key press"""
        try:
            if key == Key.space and not self.recording:
                self.audio_handler.start_recording()
                self.recording = True
            elif key == Key.esc or (hasattr(key, 'char') and key.char in ['q', 'Q']):
                print("\n👋 Exiting...")
                return False  # Stop listener
        except AttributeError:
            # Handle special keys that don't have 'char' attribute
            pass
    
    def on_release(self, key):
        """Handle key release"""
        if key == Key.space and self.recording:
            audio = self.audio_handler.stop_recording()
            self.recording = False
            
            if audio is not None and len(audio) > 0:
                # Transcribe
                query = self.audio_handler.transcribe(audio)
                
                if query:
                    # Process query
                    self.process_query(query)
                else:
                    print("⚠️  No speech detected")
            else:
                print("⚠️  No audio recorded")
        
        elif key == Key.esc:
            # Stop listener
            return False
    
    def run_cli(self):
        """Run CLI interface"""
        if not PYNPUT_AVAILABLE:
            print("\n⚠️  Audio mode requires pynput. Using text mode instead.")
            self.run_interactive()
            return
        
        print("\n" + "=" * 60)
        print("📚 Document Q&A System - Ready!")
        print("=" * 60)
        print("\nControls:")
        print("  • Hold SPACEBAR to record your question")
        print("  • Release to stop and process")
        print("  • Press ESC to quit")
        print("\nCommands (type before recording):")
        print("  • 'mode qa' - Switch to Q&A mode (default)")
        print("  • 'mode notes' - Switch to notes mode")
        print("  • 'text' - Enter text query instead of audio")
        print("  • 'list' - List saved notes")
        print("  • 'quit' - Exit")
        print("\nMode:", "📋 NOTES" if self.mode == "notes" else "💬 Q&A")
        print()
        
        # Start keyboard listener
        try:
            with Listener(on_press=self.on_press, on_release=self.on_release) as listener:
                listener.join()
        except KeyboardInterrupt:
            print("\n👋 Keyboard interrupt detected. Exiting...")
        except Exception as e:
            print(f"\n❌ Listener error: {e}")
        
        print("\n👋 Goodbye!")
    
    def run_interactive(self):
        """Run interactive text-based interface"""
        print("\n" + "=" * 60)
        print("📚 Document Q&A System - Text Mode")
        print("=" * 60)
        print("\nCommands:")
        print("  • Type your question")
        print("  • Enter a URL to browse web content")
        print("  • 'web: <url>' or 'browse: <url>' - Browse a specific URL")
        print("  • 'mode qa' or 'mode notes' - Switch modes")
        print("  • 'list' - List saved notes")
        print("  • 'quit' or 'exit' - Exit")
        print()
        
        while True:
            print(f"\n[{'NOTES' if self.mode == 'notes' else 'Q&A'}] ", end="")
            user_input = input("You: ").strip()
            
            if not user_input:
                continue
            
            if user_input.lower() in ['quit', 'exit']:
                break
            
            elif user_input.lower() == 'list':
                notes = self.notes_manager.list_notes()
                if notes:
                    print("\n📋 Saved Notes:")
                    for i, note in enumerate(notes, 1):
                        print(f"  {i}. {note.name}")
                else:
                    print("\n📋 No notes saved yet")
            
            elif user_input.lower().startswith('mode '):
                new_mode = user_input[5:].strip()
                if new_mode in ['qa', 'notes']:
                    self.mode = new_mode
                    print(f"✅ Switched to {'NOTES' if self.mode == 'notes' else 'Q&A'} mode")
                else:
                    print("⚠️  Invalid mode. Use 'qa' or 'notes'")
            
            else:
                self.process_query(user_input)
        
        print("\n👋 Goodbye!")

def main():
    app = DocQAApp()
    if not app.initialize():
        print("\n❌ Initialization failed. Please fix the issues above and try again.")
        return
    
    # Check for documents in put-your-documents-here folder
    docs_folder = "put-your-documents-here"
    if os.path.exists(docs_folder):
        doc_files = []
        for ext in ['*.txt', '*.md', '*.pdf']:
            doc_files.extend(Path(docs_folder).glob(ext))
        
        if doc_files:
            print("\n" + "=" * 60)
            print("📚 Found documents in 'put-your-documents-here' folder:")
            for i, doc in enumerate(doc_files, 1):
                print(f"  {i}. {doc.name}")
            print(f"  {len(doc_files) + 1}. ALL documents (index all files)")
            print("  0. Enter custom path")
            
            while True:
                try:
                    choice = input("\nChoose document (number or 0 for custom): ").strip()
                    if choice == '0':
                        doc_path = input("📄 Enter document path: ").strip()
                        selected_docs = [doc_path]
                        break
                    elif choice == str(len(doc_files) + 1):
                        # Select all documents
                        selected_docs = [str(doc) for doc in doc_files]
                        print(f"\n✅ Selected all {len(selected_docs)} documents")
                        break
                    else:
                        idx = int(choice) - 1
                        if 0 <= idx < len(doc_files):
                            selected_docs = [str(doc_files[idx])]
                            break
                        else:
                            print("❌ Invalid choice. Try again.")
                except ValueError:
                    print("❌ Please enter a number.")
        else:
            print(f"\n📁 No documents found in '{docs_folder}' folder.")
            doc_path = input("📄 Enter document path (txt, md, or pdf): ").strip()
            selected_docs = [doc_path]
    else:
        print(f"\n📁 '{docs_folder}' folder not found.")
        doc_path = input("📄 Enter document path (txt, md, or pdf): ").strip()
        selected_docs = [doc_path]
    
    # Check if all selected documents exist
    for doc_path in selected_docs:
        if not os.path.exists(doc_path):
            print(f"❌ File not found: {doc_path}")
            return
    
    # Load documents
    if not app.load_documents(selected_docs):
        print("❌ Failed to load documents")
        return
    
    # Choose interface mode
    print("\n" + "=" * 60)
    print("Choose interface:")
    print("  1. Audio (hold spacebar to record)")
    print("  2. Text (type queries)")
    choice = input("Choice (1/2): ").strip()
    
    if choice == '1':
        app.use_tts = True
        app.run_cli()
    else:
        app.use_tts = False
        app.run_interactive()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n👋 Interrupted. Goodbye!")
        sys.exit(0)
