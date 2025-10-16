"""
LLM handler using Ollama
"""
import requests
import json

class LLMHandler:
    def __init__(self, model: str = "llama3.2", base_url: str = "http://localhost:11434"):
        self.model = model
        self.base_url = base_url
        self.generate_url = f"{base_url}/api/generate"
        self.chat_url = f"{base_url}/api/chat"
        
    def check_connection(self) -> bool:
        """Check if Ollama is running"""
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=5)
            return response.status_code == 200
        except:
            return False
    
    def generate_response(self, context: str, query: str, mode: str = "qa", source: str = "document") -> str:
        """Generate response based on context and query
        
        Args:
            context: The context text to base the response on
            query: The user's question or request
            mode: Response mode - "qa" or "notes"
            source: Source of context - "document" or "web"
        
        Returns:
            Generated response string
        """
        
        if mode == "qa":
            if source == "web":
                prompt = (f"⚠️ NOTE: The answer is not available in the source documents. "
                         f"Using information from web search results.\n\n"
                         f"Based on the following context from web search, answer the user's question.\n\n"
                         f"Context:\n{context}\n\n"
                         f"Question: {query}\n\n"
                         f"Answer concisely and accurately based on the provided web context. "
                         f"Cite sources when possible.")
            else:
                prompt = (f"Based on the following context from the document, answer the user's question.\n\n"
                         f"Context:\n{context}\n\n"
                         f"Question: {query}\n\n"
                         f"Answer concisely and accurately based only on the provided context. "
                         f"If the answer is not in the context, say so.")

        elif mode == "notes":
            if source == "web":
                prompt = (f"⚠️ NOTE: The information is not available in the source documents. "
                         f"Using information from web search results.\n\n"
                         f"Based on the following context from web search, create structured notes in markdown format.\n\n"
                         f"Context:\n{context}\n\n"
                         f"User Request: {query}\n\n"
                         f"Create clear, well-organized notes that address the user's request. Use markdown formatting including:\n"
                         f"- Headers (##, ###)\n"
                         f"- Bullet points\n"
                         f"- Bold/italic for emphasis\n"
                         f"- Code blocks if needed\n\n"
                         f"Notes:")
            else:
                prompt = (f"Based on the following context and user request, create structured notes in markdown format.\n\n"
                         f"Context:\n{context}\n\n"
                         f"User Request: {query}\n\n"
                         f"Create clear, well-organized notes that address the user's request. Use markdown formatting including:\n"
                         f"- Headers (##, ###)\n"
                         f"- Bullet points\n"
                         f"- Bold/italic for emphasis\n"
                         f"- Code blocks if needed\n\n"
                         f"Notes:")

        else:  # general
            prompt = f"Context: {context}\n\nUser: {query}"
        
        try:
            response = requests.post(
                self.generate_url,
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False
                },
                timeout=120
            )
            
            if response.status_code == 200:
                result = response.json()
                response_text = result.get("response", "").strip()
                
                # Prepend source indicator for web-based responses
                if source == "web":
                    response_text = "🌐 **[Answer from Web Search]**\n\n" + response_text
                
                return response_text
            else:
                return f"Error: {response.status_code} - {response.text}"
        except Exception as e:
            return f"Error generating response: {str(e)}"
