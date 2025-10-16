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
    
    def search_web(self, query: str, num_results: int = 5) -> list:
        """
        Perform web search using DuckDuckGo HTML search.
        Returns a list of search results with title, url, and snippet.
        
        Args:
            query: Search query string
            num_results: Number of results to return (default 5)
            
        Returns:
            List of dicts with 'title', 'url', and 'snippet' keys
        """
        try:
            print(f"🔍 Searching the web for: {query}")
            
            # Use DuckDuckGo HTML search (no API key required)
            search_url = "https://html.duckduckgo.com/html/"
            params = {
                'q': query
            }
            
            response = self.session.post(search_url, data=params, timeout=self.timeout)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            results = []
            # Find all search result divs
            result_divs = soup.find_all('div', class_='result')
            
            for div in result_divs[:num_results]:
                try:
                    # Extract title and URL
                    title_tag = div.find('a', class_='result__a')
                    if not title_tag:
                        continue
                    
                    title = title_tag.get_text().strip()
                    url = title_tag.get('href', '')
                    
                    # Extract snippet
                    snippet_tag = div.find('a', class_='result__snippet')
                    snippet = snippet_tag.get_text().strip() if snippet_tag else ""
                    
                    if url and title:
                        results.append({
                            'title': title,
                            'url': url,
                            'snippet': snippet
                        })
                except Exception as e:
                    continue
            
            print(f"✅ Found {len(results)} web search results")
            return results
            
        except Exception as e:
            print(f"❌ Error performing web search: {e}")
            return []
    
    def fetch_and_extract_from_search_results(self, search_results: list, max_pages: int = 3) -> str:
        """
        Fetch and extract text content from search result URLs.
        
        Args:
            search_results: List of search result dictionaries
            max_pages: Maximum number of pages to fetch
            
        Returns:
            Combined text from all fetched pages
        """
        combined_text = ""
        successful_fetches = 0
        
        for i, result in enumerate(search_results[:max_pages]):
            if successful_fetches >= max_pages:
                break
                
            url = result['url']
            print(f"\n📄 Fetching content from result {i+1}: {result['title'][:60]}...")
            
            web_data = self.browse(url)
            if web_data and web_data['text']:
                # Add metadata about the source
                source_info = f"\n\n=== Source: {result['title']} ===\n"
                source_info += f"URL: {url}\n"
                source_info += f"Description: {result['snippet']}\n\n"
                combined_text += source_info + web_data['text'][:2000] + "\n\n"  # Limit to 2000 chars per page
                successful_fetches += 1
            else:
                print(f"⚠️  Failed to extract content from {url}")
        
        print(f"\n✅ Successfully fetched content from {successful_fetches} pages")
        return combined_text
