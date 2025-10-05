"""
Notes manager for saving and organizing notes
"""
import os
from datetime import datetime
from pathlib import Path

class NotesManager:
    def __init__(self, notes_dir: str = "notes"):
        self.notes_dir = Path(notes_dir)
        self.notes_dir.mkdir(exist_ok=True)
        
    def save_note(self, content: str, title: str = None) -> str:
        """Save note to file and return filepath"""
        if title:
            filename = f"{self._sanitize_filename(title)}.md"
        else:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"note_{timestamp}.md"
        
        filepath = self.notes_dir / filename
        
        # Add metadata header
        metadata = f"""---
title: {title or 'Untitled Note'}
created: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
---

"""
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(metadata + content)
        
        print(f"✅ Note saved: {filepath}")
        return str(filepath)
    
    def list_notes(self) -> list:
        """List all notes"""
        notes = list(self.notes_dir.glob("*.md"))
        return sorted(notes, key=lambda x: x.stat().st_mtime, reverse=True)
    
    def read_note(self, filepath: str) -> str:
        """Read a note file"""
        with open(filepath, 'r', encoding='utf-8') as f:
            return f.read()
    
    def _sanitize_filename(self, title: str) -> str:
        """Convert title to valid filename"""
        # Remove invalid characters
        invalid_chars = '<>:"/\\|?*'
        for char in invalid_chars:
            title = title.replace(char, '')
        
        # Replace spaces with underscores
        title = title.replace(' ', '_')
        
        # Limit length
        title = title[:50]
        
        return title or "untitled"
