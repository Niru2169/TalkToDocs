#!/usr/bin/env python3
"""
CLI Application for Document Q&A and Note Taking
"""
import os
import sys
import json
import hashlib
import time
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
        self.voice_mode = False  # Whether currently in audio/voice mode
    
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
    
    def log_qa_to_file(self, query: str, response: str, source: str = "document"):
        """Append Q&A to session log file"""
        try:
            from datetime import datetime
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            log_entry = f"""
{'='*70}
[{timestamp}] Q&A Session Log
{'='*70}
📝 Question: {query}
📌 Source: {source}
💬 Answer: {response}
{'='*70}

"""
            with open(QA_LOG_FILE, 'a', encoding='utf-8') as f:
                f.write(log_entry)
        except Exception as e:
            print(f"⚠️  Could not save to log file: {e}")
        
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
        
        # Check if query starts with "web:" or "browse:" for explicit web search
        if query.lower().startswith("web:") or query.lower().startswith("browse:"):
            search_text = query.split(":", 1)[1].strip()
            if self.web_browser.is_valid_url(search_text):
                # It's a URL - browse it
                self.process_web_query(search_text)
            else:
                # It's a search query - perform web search
                self.perform_web_search(search_text)
            return
        
        # Check if query starts with "search:" for explicit web search
        if query.lower().startswith("search:"):
            search_query = query.split(":", 1)[1].strip()
            self.perform_web_search(search_query)
            return
        
        print(f"\n🔍 Searching document...")
        
        # Search for relevant context
        results = self.doc_processor.search(query, top_k=3)
        
        if not results:
            response = "I couldn't find relevant information in the document."
            print(f"\n Response: {response}")
            # Log to file even when no results
            self.log_qa_to_file(query, response, source="document (no results)")
            if self.use_tts:
                self.tts_handler.speak(response)
            return
        
        # Combine context from document
        context = "\n\n".join([chunk for chunk, dist, meta in results])
        
        print(f"📝 Found {len(results)} relevant chunks")
        print(f"🤔 Generating response...")
        
        # Generate response from document
        response = self.llm_handler.generate_response(context, query, mode=self.mode, source="document", voice_mode=self.voice_mode)
        
        print(f"\n{'📋' if self.mode == 'notes' else '💬'} Response:\n")
        print("-" * 60)
        print(response)
        print("-" * 60)
        
        # Log Q&A to file (only in QA mode, not notes mode)
        if self.mode == "qa":
            self.log_qa_to_file(query, response, source="document")
        
        # Save notes if in notes mode
        if self.mode == "notes":
            save = input("\n💾 Save this note? (y/n): ").strip().lower()
            if save == 'y':
                title = input("Note title (or press Enter for auto): ").strip()
                self.notes_manager.save_note(response, title or None)
        
        # Speak response
        if self.use_tts:
            self.tts_handler.speak(response)
    
    def perform_web_search(self, search_query: str):
        """Perform a web search and provide results"""
        print(f"\n🔍 Searching the web for: {search_query}")
        
        try:
            # Perform web search
            search_results = self.web_browser.search_web(search_query, num_results=5)
            
            if not search_results:
                response = "No search results found."
                print(f"\n💬 Response: {response}")
                # Log to file even when no results
                self.log_qa_to_file(search_query, response, source="web (no results)")
                if self.use_tts:
                    self.tts_handler.speak(response)
                return
            
            # Display top results
            print(f"\n📊 Top results:")
            for i, result in enumerate(search_results[:3], 1):
                print(f"  {i}. {result['title']}")
                if result['snippet']:
                    print(f"     {result['snippet'][:150]}...")
            
            # Fetch and extract content from top result
            print(f"\n📄 Fetching content from top result...")
            web_content = self.web_browser.fetch_and_extract_from_search_results(search_results, max_pages=1)
            
            if not web_content or len(web_content.strip()) < 50:
                # If can't fetch content, just provide snippet summary
                snippets = [r['snippet'] for r in search_results[:2] if r['snippet']]
                response = "\n".join(snippets) if snippets else "Could not extract content from search results."
            else:
                # Generate response based on fetched content
                initial_response = self.llm_handler.generate_response(web_content, search_query, mode=self.mode, voice_mode=self.voice_mode)
                
                # Pass through summarization prompt to extract key information
                summary_prompt = f"""Based on this information about "{search_query}", provide just the gist - the most important key points in 2-3 sentences:

{initial_response}

Focus on: {search_query}"""
                
                response = self.llm_handler.generate_response(summary_prompt, search_query, mode=self.mode, voice_mode=self.voice_mode)
            
            print(f"\n💬 Response:\n")
            print("-" * 60)
            print(response)
            print("-" * 60)
            
            # Log Q&A to file (only in QA mode, not notes mode)
            if self.mode == "qa":
                self.log_qa_to_file(search_query, response, source="web")
            
            # Save notes if in notes mode
            if self.mode == "notes":
                save = input("\n💾 Save this note? (y/n): ").strip().lower()
                if save == 'y':
                    title = input("Note title (or press Enter for auto): ").strip()
                    self.notes_manager.save_note(response, title or None)
            
            # Speak response
            if self.use_tts:
                self.tts_handler.speak(response)
        
        except Exception as e:
            print(f"\n❌ Error performing web search: {e}")
    
    def process_web_search_fallback(self, query: str) -> str:
        """
        Perform web search and extract content from results as fallback
        when document search yields no results.
        
        Args:
            query: User's search query
            
        Returns:
            Generated response based on web search results
        """
        # Perform web search
        search_results = self.web_browser.search_web(query, num_results=5)
        
        if not search_results:
            response = "I couldn't find relevant information in the document, and web search also returned no results."
            return response
        
        # Display search results
        print(f"\n📊 Top search results:")
        for i, result in enumerate(search_results[:3], 1):
            print(f"  {i}. {result['title']}")
            print(f"     {result['url']}")
            if result['snippet']:
                print(f"     {result['snippet'][:100]}...")
        
        # Fetch and extract content from top results
        web_content = self.web_browser.fetch_and_extract_from_search_results(search_results, max_pages=3)
        
        if not web_content or len(web_content.strip()) < 100:
            response = "I couldn't find relevant information in the document, and failed to extract useful content from web search results."
            return response
        
        print(f"\n🤔 Generating response from web content...")
        
        # Generate response using web content
        response = self.llm_handler.generate_response(web_content, query, mode=self.mode, source="web")
        
        return response
    
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
        print("\n💡 Type 'back' or 'exit' to return to document mode")
        
        # Loop to handle multiple queries about the web page
        is_first_query = True
        while True:
            if is_first_query:
                web_query = input("\n💬 What would you like to know about this page? (or press Enter for summary): ").strip()
            else:
                web_query = input("\n💬 Ask another question (or type 'back'/'exit' to return): ").strip()
            
            # Check if user wants to exit browsing mode
            if web_query.lower() in ['back', 'exit']:
                print("📚 Returning to document mode...")
                break
            
            # Handle empty input
            if not web_query:
                if is_first_query:
                    # Empty input on first query, provide default summary
                    web_query = "Summarize the main content of this page"
                else:
                    # Empty input after first query, show hint and continue
                    print("💡 Type a question or 'back' to return to document mode")
                    continue
            
            # Mark that we've processed the first query
            is_first_query = False
            
            # Search web content
            results = self.doc_processor.search(web_query, top_k=3)
            
            if results:
                context = "\n\n".join([chunk for chunk, dist, meta in results])
                print(f"\n🤔 Generating response based on web content...")
                
                # Generate response
                response = self.llm_handler.generate_response(context, web_query, mode=self.mode, source="document")
                
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
        
        # Restore original index when exiting browsing mode
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
        
        # Enable voice mode for casual responses
        self.voice_mode = True
        
        print("\n" + "=" * 60)
        print("📚 Document Q&A System - Ready!")
        print("=" * 60)
        print("\nControls:")
        print("  • Hold SPACEBAR to record your question")
        print("  • Release to stop and process")
        print("  • Press ESC or Ctrl+C to quit")
        print("\nCommands (type before recording):")
        print("  • 'mode qa' - Switch to Q&A mode (default)")
        print("  • 'mode notes' - Switch to notes mode")
        print("  • 'text' - Enter text query instead of audio")
        print("  • 'list' - List saved notes")
        print("  • 'quit' - Exit")
        print("\nMode:", "📋 NOTES" if self.mode == "notes" else "💬 Q&A")
        print()
        
        # Start keyboard listener with interrupt handling
        listener = None
        try:
            listener = Listener(on_press=self.on_press, on_release=self.on_release)
            listener.start()
            
            # Main loop to check for interrupts
            while listener.is_alive():
                try:
                    # Check for KeyboardInterrupt more frequently
                    import signal
                    def signal_handler(signum, frame):
                        raise KeyboardInterrupt
                    
                    # Set up signal handler for SIGINT (Ctrl+C)
                    old_handler = signal.signal(signal.SIGINT, signal_handler)
                    
                    # Small delay while checking for interrupts
                    time.sleep(0.1)
                    
                    # Restore original handler
                    signal.signal(signal.SIGINT, old_handler)
                    
                except KeyboardInterrupt:
                    print("\n👋 Keyboard interrupt detected. Exiting...")
                    break
                    
        except KeyboardInterrupt:
            print("\n👋 Keyboard interrupt detected. Exiting...")
        except Exception as e:
            print(f"\n❌ Listener error: {e}")
        finally:
            if listener:
                listener.stop()
        
        print("\n👋 Goodbye!")
    
    def run_interactive(self):
        """Run interactive text-based interface"""
        # Disable voice mode for text interface
        self.use_tts = False
        self.voice_mode = False
        
        print("\n" + "=" * 60)
        print("📚 Document Q&A System - Text Mode")
        print("=" * 60)
        print("\nCommands:")
        print("  • Type your question")
        print("  • 'web: <url>' or 'browse: <url>' - Browse web content explicitly")
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
        
        # Search for documents recursively, including in symlinked folders
        docs_path = Path(docs_folder)
        
        # Define supported extensions
        supported_exts = ['.txt', '.md', '.pdf']
        
        # Recursively search for documents
        # Using rglob to find files recursively, including in symlinked directories
        for ext in supported_exts:
            doc_files.extend(docs_path.rglob(f'*{ext}'))
        
        # Convert to list of strings and remove duplicates while preserving order
        doc_files = list(dict.fromkeys(str(doc) for doc in doc_files))
        doc_files.sort()  # Sort for consistent ordering
        
        if doc_files:
            print("\n" + "=" * 60)
            print("📚 Found documents in 'put-your-documents-here' folder (including subdirectories):")
            for i, doc in enumerate(doc_files, 1):
                # Show relative path for clarity
                rel_path = Path(doc).relative_to(docs_path)
                print(f"  {i}. {rel_path}")
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
                        selected_docs = doc_files
                        print(f"\n✅ Selected all {len(selected_docs)} documents")
                        break
                    else:
                        idx = int(choice) - 1
                        if 0 <= idx < len(doc_files):
                            selected_docs = [doc_files[idx]]
                            break
                        else:
                            print("❌ Invalid choice. Try again.")
                except ValueError:
                    print("❌ Please enter a number.")
        else:
            print(f"\n📁 No documents found in '{docs_folder}' folder or its subdirectories.")
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
