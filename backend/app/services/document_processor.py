import os
from typing import List, Dict, Any
import logging
from pathlib import Path
import json
import re

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
    
    def _chunk_text(self, text: str, chunk_size: int = 1000, overlap: int = 200) -> List[str]:
        """
        Smart semantic chunking preserving paragraph structure.
        Uses recursive splitting tailored for RAG.
        """
        if not text:
            return []
            
        # normalize whitespace but keep newlines for paragraph detection
        text = re.sub(r'[ \t]+', ' ', text)
        
        # Split by double newlines (paragraphs)
        paragraphs = re.split(r'\n\s*\n', text)
        
        chunks = []
        current_chunk = []
        current_length = 0
        
        for para in paragraphs:
            para = para.strip()
            if not para:
                continue
                
            # If paragraph itself is too large, split it by sentences
            if len(para) > chunk_size:
                # Process large paragraph
                sentences = re.split(r'(?<=[.!?])\s+', para)
                for sentence in sentences:
                    if current_length + len(sentence) > chunk_size and current_chunk:
                        chunks.append(' '.join(current_chunk))
                        
                        # Overlap
                        overlap_text = ""
                        overlap_len = 0
                        for i in range(len(current_chunk)-1, -1, -1):
                            if overlap_len + len(current_chunk[i]) > overlap:
                                break
                            overlap_text = current_chunk[i] + " " + overlap_text
                            overlap_len += len(current_chunk[i])
                            
                        current_chunk = [overlap_text.strip()] if overlap_text.strip() else []
                        current_length = len(current_chunk[0]) if current_chunk else 0
                        
                    current_chunk.append(sentence)
                    current_length += len(sentence)
            else:
                # Standard paragraph handling
                if current_length + len(para) > chunk_size and current_chunk:
                    chunks.append(' '.join(current_chunk))
                    
                    # Simple overlap for paragraphs
                    overlap_text = current_chunk[-1] if current_chunk else ""
                    if len(overlap_text) > overlap:
                        overlap_text = overlap_text[-overlap:]
                    
                    current_chunk = [overlap_text] if overlap_text else []
                    current_length = len(overlap_text)
                    
                current_chunk.append(para)
                current_length += len(para)
        
        if current_chunk:
            chunks.append(' '.join(current_chunk))
            
        return chunks if chunks else [text]  # Fallback to full text if no chunks created
    
    async def process_files_batch(self, file_paths: List[str], metadata_list: List[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Process multiple files in parallel for better performance.
        """
        import asyncio
        
        if metadata_list is None:
            metadata_list = [None] * len(file_paths)
        elif len(metadata_list) != len(file_paths):
            raise ValueError("metadata_list must have same length as file_paths")
        
        # Create tasks for parallel processing
        tasks = [
            self.process_file(file_path, metadata) 
            for file_path, metadata in zip(file_paths, metadata_list)
        ]
        
        # Execute all tasks concurrently
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Flatten results and handle any exceptions
        all_documents = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Error processing file {file_paths[i]}: {result}")
                continue
            all_documents.extend(result)
        
        return all_documents
