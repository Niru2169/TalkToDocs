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
    
    def generate_response(self, context: str, query: str, mode: str = "qa") -> str:
        """Generate response based on context and query"""
        
        if mode == "qa":
            prompt = (f"Based on the following context from the document, answer the user's question.\n\n"
                     f"Context:\n{context}\n\n"
                     f"Question: {query}\n\n"
                     f"Answer concisely and accurately based only on the provided context. "
                     f"If the answer is not in the context, say so.")

        elif mode == "notes":
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
                return result.get("response", "").strip()
            else:
                return f"Error: {response.status_code} - {response.text}"
        except Exception as e:
            return f"Error generating response: {str(e)}"
