#!/usr/bin/env python3
"""
CLI Application for Document Q&A and Note Taking
"""
import os
import sys
from pathlib import Path

from config import *
from document_processor import DocumentProcessor
from audio_handler import AudioHandler
from tts_handler import TTSHandler
from llm_handler import LLMHandler
from notes_manager import NotesManager

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
        self.recording = False
        self.mode = "qa"  # "qa" or "notes"
        
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
            print("⚠️  Warning: Ollama not running. Start it with: ollama serve")
        
        # Initialize notes manager
        self.notes_manager = NotesManager(NOTES_DIR)
        
        print("\n✅ Initialization complete!")
    
    def load_document(self, file_path: str):
        """Load and index a document"""
        print(f"\n📄 Loading document: {file_path}")
        
        # Check if index exists
        if os.path.exists(FAISS_INDEX_PATH):
            print("Found existing index. Load it? (y/n): ", end="")
            choice = input().strip().lower()
            if choice == 'y':
                if self.doc_processor.load_index(FAISS_INDEX_PATH):
                    print("✅ Index loaded successfully!")
                    return True
        
        # Index the document
        self.doc_processor.index_document(file_path)
        
        # Check if indexing was successful
        if self.doc_processor.index is None or self.doc_processor.index.ntotal == 0:
            print("❌ Failed to index document. Please check the file and try again.")
            return False
        
        # Save the index
        self.doc_processor.save_index(FAISS_INDEX_PATH)
        
        print("✅ Document loaded and indexed!")
        return True
    
    def process_query(self, query: str):
        """Process user query and generate response"""
        if not query:
            return
        
        print(f"\n🔍 Searching document...")
        
        # Search for relevant context
        results = self.doc_processor.search(query, top_k=3)
        
        if not results:
            response = "I couldn't find relevant information in the document."
            print(f"\n💬 Response: {response}")
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
        self.tts_handler.speak(response)
    
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
    app.initialize()
    
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
            print("  0. Enter custom path")
            
            while True:
                try:
                    choice = input("\nChoose document (number or 0 for custom): ").strip()
                    if choice == '0':
                        doc_path = input("📄 Enter document path: ").strip()
                        break
                    else:
                        idx = int(choice) - 1
                        if 0 <= idx < len(doc_files):
                            doc_path = str(doc_files[idx])
                            break
                        else:
                            print("❌ Invalid choice. Try again.")
                except ValueError:
                    print("❌ Please enter a number.")
        else:
            print(f"\n📁 No documents found in '{docs_folder}' folder.")
            doc_path = input("📄 Enter document path (txt, md, or pdf): ").strip()
    else:
        print(f"\n📁 '{docs_folder}' folder not found.")
        doc_path = input("📄 Enter document path (txt, md, or pdf): ").strip()
    
    if not os.path.exists(doc_path):
        print(f"❌ File not found: {doc_path}")
        return
    
    # Load document
    if not app.load_document(doc_path):
        print("❌ Failed to load document")
        return
    
    # Choose interface mode
    print("\n" + "=" * 60)
    print("Choose interface:")
    print("  1. Audio (hold spacebar to record)")
    print("  2. Text (type queries)")
    choice = input("Choice (1/2): ").strip()
    
    if choice == '1':
        app.run_cli()
    else:
        app.run_interactive()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n👋 Interrupted. Goodbye!")
        sys.exit(0)
