import os
from typing import List, Dict, Any
import logging
from pathlib import Path
import json

# Import optional dependencies
try:
    import pypdf
except ImportError:
    pypdf = None

try:
    import pandas as pd
except ImportError:
    pd = None

try:
    import openpyxl
except ImportError:
    openpyxl = None

logger = logging.getLogger(__name__)

class DocumentProcessor:
    def __init__(self, upload_dir: str = "uploads"):
        self.upload_dir = Path(upload_dir)
        self.upload_dir.mkdir(exist_ok=True)
    
    async def process_file(self, file_path: str, metadata: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """
        Process a file and return a list of document chunks.
        """
        file_path = Path(file_path)
        if not file_path.exists():
            raise FileNotFoundError(f"File {file_path} not found")
            
        ext = file_path.suffix.lower()
        content = ""
        
        try:
            if ext == '.pdf':
                content = self._process_pdf(file_path)
            elif ext in ['.csv', '.xlsx', '.xls']:
                content = self._process_spreadsheet(file_path)
            elif ext == '.txt':
                content = self._process_txt(file_path)
            else:
                # Try as text for other extensions
                content = self._process_txt(file_path)
                
            # Simple chunking by paragraphs or size
            chunks = self._chunk_text(content)
            
            documents = []
            for i, chunk in enumerate(chunks):
                documents.append({
                    "text": chunk,
                    "source": file_path.name,
                    "metadata": {
                        **(metadata or {}),
                        "chunk_id": i,
                        "file_type": ext
                    }
                })
            
            return documents
            
        except Exception as e:
            logger.error(f"Error processing file {file_path}: {e}")
            raise

    def _process_pdf(self, file_path: Path) -> str:
        if not pypdf:
            raise ImportError("pypdf is required for PDF processing")
        
        text = ""
        with open(file_path, 'rb') as f:
            reader = pypdf.PdfReader(f)
            for page in reader.pages:
                extracted = page.extract_text()
                if extracted:
                    text += extracted + "\n"
        return text

    def _process_spreadsheet(self, file_path: Path) -> str:
        if not pd:
            raise ImportError("pandas is required for spreadsheet processing")
            
        if file_path.suffix == '.csv':
            df = pd.read_csv(file_path)
        else:
            if not openpyxl and file_path.suffix in ['.xlsx', '.xlsm']:
                 raise ImportError("openpyxl is required for Excel processing")
            df = pd.read_excel(file_path)
            
        # Convert to string representation
        return df.to_string(index=False)

    def _process_txt(self, file_path: Path) -> str:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            return f.read()
            
    def _chunk_text(self, text: str, chunk_size: int = 1000, overlap: int = 100) -> List[str]:
        """Simple text chunking"""
        if not text:
            return []
            
        chunks = []
        start = 0
        text_len = len(text)
        
        while start < text_len:
            end = start + chunk_size
            
            # Try to find a sentence break
            if end < text_len:
                # Look for the last period/newline in the window
                last_break = max(
                    text.rfind('.', start, end),
                    text.rfind('\n', start, end)
                )
                if last_break > start + chunk_size // 2:
                    end = last_break + 1
            
            chunk = text[start:end].strip()
            if chunk:
                chunks.append(chunk)
            
            start = end - overlap
            
        return chunks
