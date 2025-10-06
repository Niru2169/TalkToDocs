"""
Web browsing and content extraction module
"""
import requests
from bs4 import BeautifulSoup
from typing import Optional, Dict
from urllib.parse import urlparse
import re

class WebBrowser:
    def __init__(self, timeout: int = 10, user_agent: Optional[str] = None):
        self.timeout = timeout
        self.user_agent = user_agent or "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        self.session = requests.Session()
        self.session.headers.update({'User-Agent': self.user_agent})
    
    def is_valid_url(self, url: str) -> bool:
        """Check if URL is valid"""
        try:
            result = urlparse(url)
            return all([result.scheme, result.netloc])
        except:
            return False
    
    def fetch_url(self, url: str) -> Optional[str]:
        """Fetch content from URL"""
        if not self.is_valid_url(url):
            print(f"❌ Invalid URL: {url}")
            return None
        
        try:
            print(f"🌐 Fetching content from: {url}")
            response = self.session.get(url, timeout=self.timeout)
            response.raise_for_status()
            return response.text
        except requests.exceptions.Timeout:
            print(f"❌ Request timeout for: {url}")
            return None
        except requests.exceptions.RequestException as e:
            print(f"❌ Error fetching URL: {e}")
            return None
    
    def extract_text(self, html: str) -> str:
        """Extract readable text from HTML"""
        try:
            soup = BeautifulSoup(html, 'html.parser')
            
            # Remove script and style elements
            for script in soup(["script", "style", "nav", "footer", "header"]):
                script.decompose()
            
            # Get text
            text = soup.get_text(separator='\n')
            
            # Clean up text
            lines = (line.strip() for line in text.splitlines())
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
            text = '\n'.join(chunk for chunk in chunks if chunk)
            
            return text
        except Exception as e:
            print(f"❌ Error extracting text: {e}")
            return ""
    
    def extract_metadata(self, html: str) -> Dict[str, str]:
        """Extract metadata from HTML"""
        metadata = {
            "title": "",
            "description": "",
            "keywords": ""
        }
        
        try:
            soup = BeautifulSoup(html, 'html.parser')
            
            # Extract title
            title_tag = soup.find('title')
            if title_tag:
                metadata["title"] = title_tag.get_text().strip()
            
            # Extract meta description
            desc_tag = soup.find('meta', attrs={'name': 'description'})
            if desc_tag and desc_tag.get('content'):
                metadata["description"] = desc_tag['content'].strip()
            
            # Extract keywords
            keywords_tag = soup.find('meta', attrs={'name': 'keywords'})
            if keywords_tag and keywords_tag.get('content'):
                metadata["keywords"] = keywords_tag['content'].strip()
        
        except Exception as e:
            print(f"⚠️  Error extracting metadata: {e}")
        
        return metadata
    
    def browse(self, url: str) -> Optional[Dict[str, str]]:
        """Browse URL and extract content and metadata"""
        html = self.fetch_url(url)
        
        if not html:
            return None
        
        text = self.extract_text(html)
        metadata = self.extract_metadata(html)
        
        if not text:
            print("⚠️  No text content extracted from URL")
            return None
        
        print(f"✅ Extracted {len(text)} characters from {metadata.get('title', url)}")
        
        return {
            "url": url,
            "text": text,
            "title": metadata.get("title", ""),
            "description": metadata.get("description", ""),
            "keywords": metadata.get("keywords", "")
        }
    
    def search_web(self, query: str) -> str:
        """
        Simple web search simulation.
        Note: This is a placeholder. For real web search, you would need
        to integrate with a search API (Google Custom Search, Bing, etc.)
        """
        return f"Web search for '{query}' would require API integration with search engines like Google Custom Search or Bing."
