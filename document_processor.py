"""
Document processing and indexing with FAISS
"""
import os
import pickle
from typing import List, Tuple
import numpy as np
import faiss
from sentence_transformers import SentenceTransformer
from pathlib import Path
import io

class DocumentProcessor:
    def __init__(self, model_name: str, chunk_size: int = 500, chunk_overlap: int = 50):
        self.model = SentenceTransformer(model_name)
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.index = None
        self.chunks = []
        self.metadata = []
        self.use_image_extraction = True  # Enable image extraction by default
    
    def extract_images_from_pdf(self, file_path: str) -> List[dict]:
        """Extract images from PDF and perform OCR"""
        images_data = []
        
        try:
            import fitz  # PyMuPDF
            from PIL import Image
            
            # Try to import pytesseract for OCR
            try:
                import pytesseract
                ocr_available = True
            except ImportError:
                ocr_available = False
                print("  ⚠️  pytesseract not available. Image OCR will be skipped.")
                print("     To enable OCR: Install Tesseract OCR system package, then: pip install pytesseract")
            
            doc = fitz.open(file_path)
            
            for page_num in range(len(doc)):
                page = doc[page_num]
                image_list = page.get_images()
                
                for img_index, img in enumerate(image_list):
                    try:
                        xref = img[0]
                        base_image = doc.extract_image(xref)
                        image_bytes = base_image["image"]
                        
                        # Convert to PIL Image for OCR
                        if ocr_available:
                            image = Image.open(io.BytesIO(image_bytes))
                            
                            # Perform OCR on the image
                            try:
                                ocr_text = pytesseract.image_to_string(image)
                                ocr_text = ocr_text.strip()
                                
                                if ocr_text:
                                    images_data.append({
                                        'page': page_num + 1,
                                        'image_index': img_index + 1,
                                        'text': ocr_text,
                                        'type': 'image_ocr'
                                    })
                                    print(f"    📷 Page {page_num + 1}, Image {img_index + 1}: Extracted {len(ocr_text)} characters via OCR")
                            except Exception as e:
                                print(f"    ⚠️  OCR failed for image {img_index + 1} on page {page_num + 1}: {e}")
                        
                    except Exception as e:
                        print(f"    ⚠️  Failed to process image {img_index + 1} on page {page_num + 1}: {e}")
                        continue
            
            doc.close()
            
        except ImportError:
            print("  ℹ️  PyMuPDF (fitz) not installed. Image extraction from PDFs will be skipped.")
            print("     Install with: pip install PyMuPDF Pillow pytesseract")
        except Exception as e:
            print(f"  ⚠️  Error extracting images: {e}")
        
        return images_data
        
    def load_document(self, file_path: str) -> str:
        """Load document from various formats"""
        path = Path(file_path)
        
        if path.suffix == '.txt':
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        elif path.suffix == '.md':
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        elif path.suffix == '.pdf':
            # Try PyMuPDF first (better for images and complex PDFs)
            try:
                import fitz  # PyMuPDF
                text = []
                doc = fitz.open(file_path)
                print(f"PDF has {len(doc)} pages")
                
                for i, page in enumerate(doc):
                    page_text = page.get_text()
                    if page_text:
                        text.append(page_text)
                    print(f"  Page {i+1}: {len(page_text) if page_text else 0} characters")
                
                doc.close()
                
                # Extract images if enabled
                if self.use_image_extraction:
                    print(f"  🖼️  Extracting images from PDF...")
                    images_data = self.extract_images_from_pdf(file_path)
                    
                    if images_data:
                        print(f"  ✅ Extracted text from {len(images_data)} images")
                        # Append image OCR text to the document
                        for img_data in images_data:
                            text.append(f"\n[Image from page {img_data['page']}, Image {img_data['image_index']}]:\n{img_data['text']}")
                    else:
                        print(f"  ℹ️  No images with extractable text found")
                
                return '\n\n'.join(text)
                
            except ImportError:
                # Fallback to PyPDF2 if PyMuPDF is not available
                print("  ℹ️  PyMuPDF not installed. Falling back to PyPDF2 (no image support).")
                try:
                    import PyPDF2
                    text = []
                    with open(file_path, 'rb') as f:
                        reader = PyPDF2.PdfReader(f)
                        print(f"PDF has {len(reader.pages)} pages")
                        for i, page in enumerate(reader.pages):
                            page_text = page.extract_text()
                            if page_text:
                                text.append(page_text)
                            print(f"  Page {i+1}: {len(page_text) if page_text else 0} characters")
                    return '\n\n'.join(text)
                except ImportError:
                    print("❌ Neither PyMuPDF nor PyPDF2 installed.")
                    print("   For image support with OCR:")
                    print("     1. Install Tesseract OCR (system package)")
                    print("     2. pip install PyMuPDF Pillow pytesseract")
                    print("   For basic PDF support: pip install PyPDF2")
                    print("   See README.md for detailed installation instructions")
                    return ""
                except Exception as e:
                    print(f"❌ Error reading PDF with PyPDF2: {e}")
                    return ""
            except Exception as e:
                print(f"❌ Error reading PDF: {e}")
                return ""
        else:
            print(f"Unsupported file format: {path.suffix}")
            return ""
    
    def chunk_text(self, text: str) -> List[str]:
        """Split text into overlapping chunks"""
        chunks = []
        start = 0
        
        while start < len(text):
            end = start + self.chunk_size
            chunk = text[start:end]
            
            # Try to break at sentence boundary
            if end < len(text):
                last_period = chunk.rfind('.')
                last_newline = chunk.rfind('\n')
                break_point = max(last_period, last_newline)
                
                if break_point > self.chunk_size * 0.5:
                    chunk = chunk[:break_point + 1]
                    end = start + break_point + 1
            
            chunks.append(chunk.strip())
            start = end - self.chunk_overlap
        
        return [c for c in chunks if c]
    
    def index_document(self, file_path: str):
        """Process and index a document"""
        print(f"Loading document: {file_path}")
        text = self.load_document(file_path)
        
        if not text:
            print("❌ Failed to load document or document is empty")
            return
        
        print(f"Document loaded: {len(text)} characters")
        
        if len(text) < 50:
            print("⚠️  Warning: Document seems too short. Check if it loaded correctly.")
            print(f"Content preview: {text[:200]}")
        
        print("Chunking document...")
        self.chunks = self.chunk_text(text)
        
        if not self.chunks:
            print("❌ Failed to create chunks. Document might be too short or empty.")
            return
        
        print(f"Created {len(self.chunks)} chunks")
        
        self.metadata = [{"source": file_path, "chunk_id": i} for i in range(len(self.chunks))]
        
        print("Generating embeddings...")
        embeddings = self.model.encode(self.chunks, show_progress_bar=True)
        
        if embeddings.ndim == 1:
            embeddings = embeddings.reshape(1, -1)
        
        print("Building FAISS index...")
        dimension = embeddings.shape[1]
        self.index = faiss.IndexFlatL2(dimension)
        self.index.add(embeddings.astype('float32'))
        
        print(f"✅ Index built with {self.index.ntotal} vectors")
    
    def search(self, query: str, top_k: int = 3) -> List[Tuple[str, float, dict]]:
        """Search for relevant chunks"""
        if self.index is None or self.index.ntotal == 0:
            return []
        
        query_embedding = self.model.encode([query])
        distances, indices = self.index.search(query_embedding.astype('float32'), top_k)
        
        results = []
        for dist, idx in zip(distances[0], indices[0]):
            if idx < len(self.chunks):
                results.append((self.chunks[idx], float(dist), self.metadata[idx]))
        
        return results
    
    def save_index(self, index_path: str):
        """Save FAISS index and metadata"""
        if self.index is None:
            print("No index to save")
            return
        
        faiss.write_index(self.index, index_path)
        
        metadata_path = index_path.replace('.faiss', '_metadata.pkl')
        with open(metadata_path, 'wb') as f:
            pickle.dump({
                'chunks': self.chunks,
                'metadata': self.metadata
            }, f)
        
        print(f"Index saved to {index_path}")
    
    def load_index(self, index_path: str):
        """Load FAISS index and metadata"""
        if not os.path.exists(index_path):
            print(f"Index not found: {index_path}")
            return False
        
        self.index = faiss.read_index(index_path)
        
        metadata_path = index_path.replace('.faiss', '_metadata.pkl')
        with open(metadata_path, 'rb') as f:
            data = pickle.load(f)
            self.chunks = data['chunks']
            self.metadata = data['metadata']
        
        print(f"Index loaded: {self.index.ntotal} vectors")
        return True
