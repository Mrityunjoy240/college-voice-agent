from pypdf import PdfReader
import pandas as pd
from typing import List, Dict
import os

class DocumentProcessor:
    """Process various document formats and extract text chunks."""
    
    def __init__(self, chunk_size: int = 1000, chunk_overlap: int = 200):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
    
    def process_file(self, file_path: str) -> List[Dict[str, str]]:
        """Process a file and return text chunks with metadata."""
        ext = os.path.splitext(file_path)[1].lower()
        
        if ext == '.pdf':
            return self._process_pdf(file_path)
        elif ext in ['.xlsx', '.xls']:
            return self._process_excel(file_path)
        elif ext == '.csv':
            return self._process_csv(file_path)
        elif ext == '.txt':
            return self._process_text(file_path)
        else:
            raise ValueError(f"Unsupported file type: {ext}")
    
    def _process_pdf(self, file_path: str) -> List[Dict[str, str]]:
        """Extract text from PDF and create chunks."""
        chunks = []
        reader = PdfReader(file_path)
        
        for page_num, page in enumerate(reader.pages, start=1):
            text = page.extract_text()
            if text:
                # Basic cleaning
                text = self._clean_text(text)
                page_chunks = self._create_chunks(text)
                
                for i, chunk in enumerate(page_chunks):
                    chunks.append({
                        'text': chunk,
                        'source': os.path.basename(file_path),
                        'page': page_num,
                        'chunk_id': f"{page_num}_{i}"
                    })
        
        return chunks

    def _clean_text(self, text: str) -> str:
        """Clean extracted text."""
        import re
        
        # Remove null characters
        text = text.replace('\x00', '')
        
        # specific fix for the "Word\n \nWord" artifact seen in the logs
        text = text.replace('\n \n', ' ')
        
        # Normalize whitespace
        # Replace 3+ newlines with double newline (paragraph break)
        text = re.sub(r'\n{3,}', '\n\n', text)
        
        # Join hyphenated words split across lines (e.g. "engine-\nering")
        text = re.sub(r'(\w+)-\n(\w+)', r'\1\2', text)
        
        # Replace single newlines within sentences with space
        # (Lookbehind for non-punctuation, lookahead for non-newline)
        # This fixes "Word\nWord" becoming "Word Word"
        text = re.sub(r'(?<!\n)\n(?!\n)', ' ', text)
        
        # Remove weird PDF artifacts like " . . . "
        text = re.sub(r'\s\.\s\.\s\.', '...', text)
        
        # Collapse multiple spaces
        text = re.sub(r' +', ' ', text)
        
        return text.strip()
    
    def _process_excel(self, file_path: str) -> List[Dict[str, str]]:
        """Extract text from Excel file."""
        chunks = []
        df = pd.read_excel(file_path, sheet_name=None)  # Read all sheets
        
        for sheet_name, sheet_df in df.items():
            # Convert DataFrame to text
            text = sheet_df.to_string(index=False)
            sheet_chunks = self._create_chunks(text)
            
            for i, chunk in enumerate(sheet_chunks):
                chunks.append({
                    'text': chunk,
                    'source': os.path.basename(file_path),
                    'sheet': sheet_name,
                    'chunk_id': f"{sheet_name}_{i}"
                })
        
        return chunks
    
    def _process_csv(self, file_path: str) -> List[Dict[str, str]]:
        """Extract text from CSV file."""
        chunks = []
        df = pd.read_csv(file_path)
        text = df.to_string(index=False)
        csv_chunks = self._create_chunks(text)
        
        for i, chunk in enumerate(csv_chunks):
            chunks.append({
                'text': chunk,
                'source': os.path.basename(file_path),
                'chunk_id': str(i)
            })
        
        return chunks
    
    def _process_text(self, file_path: str) -> List[Dict[str, str]]:
        """Extract text from plain text file."""
        chunks = []
        with open(file_path, 'r', encoding='utf-8') as f:
            text = f.read()
        
        text_chunks = self._create_chunks(text)
        
        for i, chunk in enumerate(text_chunks):
            chunks.append({
                'text': chunk,
                'source': os.path.basename(file_path),
                'chunk_id': str(i)
            })
        
        return chunks
    
    def _create_chunks(self, text: str) -> List[str]:
        """Split text into overlapping chunks respecting sentence boundaries."""
        if not text.strip():
            return []
        
        # First, split into sentences to avoid breaking context
        sentences = self._split_into_sentences(text)
        chunks = []
        current_chunk = []
        current_length = 0
        
        for sentence in sentences:
            sentence_len = len(sentence)
            
            # If a single sentence is too long, we must split it hard
            if sentence_len > self.chunk_size:
                # If we have a current chunk building up, save it first
                if current_chunk:
                    chunks.append(" ".join(current_chunk))
                    current_chunk = []
                    current_length = 0
                
                # Split the long sentence by characters
                for i in range(0, sentence_len, self.chunk_size - self.chunk_overlap):
                    chunks.append(sentence[i:i + self.chunk_size])
                continue

            # Check if adding this sentence would exceed chunk size
            if current_length + sentence_len + 1 > self.chunk_size:
                # Save current chunk
                chunks.append(" ".join(current_chunk))
                
                # Start new chunk with overlap if possible (simplified here: just start new)
                # To do overlap correctly with sentences is tricky, so we'll do a simple overlap
                # by keeping the last few sentences if they fit.
                
                # Simple sliding window approach for sentences:
                # Keep last sentence as overlap for the next chunk
                overlap_text = current_chunk[-1] if current_chunk else ""
                current_chunk = [overlap_text, sentence] if overlap_text else [sentence]
                current_length = len(overlap_text) + 1 + sentence_len if overlap_text else sentence_len
            else:
                current_chunk.append(sentence)
                current_length += sentence_len + 1
        
        # Add the last chunk
        if current_chunk:
            chunks.append(" ".join(current_chunk))
            
        return chunks

    def _split_into_sentences(self, text: str) -> List[str]:
        """Simple rule-based sentence splitter."""
        # Replace common abbreviations to avoid false positives (basic list)
        text = text.replace("Mr.", "Mr").replace("Mrs.", "Mrs").replace("Dr.", "Dr").replace("vs.", "vs")
        
        # Split by common sentence terminators
        import re
        # Split on . ? ! followed by a space or newline
        # We keep the delimiter to re-attach it
        parts = re.split(r'([.?!])\s+', text)
        
        sentences = []
        current = ""
        for i in range(0, len(parts) - 1, 2):
            sentence = parts[i] + parts[i+1]
            sentences.append(sentence.strip())
            
        if len(parts) % 2 == 1 and parts[-1]:
            sentences.append(parts[-1].strip())
            
        return [s for s in sentences if s]
