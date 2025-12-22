from groq import Groq, AsyncGroq
from typing import List, Dict, Optional, AsyncGenerator
from app.config import settings
import json
import os
import difflib
import math
import re
import asyncio
from collections import defaultdict, Counter
from concurrent.futures import ThreadPoolExecutor

class RAGService:
    """Simplified RAG service using Groq API with optimized BM25 retrieval."""
    
    def __init__(self):
        # Groq client configuration (0.5 second responses!)
        self.client = Groq(api_key=settings.groq_api_key)
        self.async_client = AsyncGroq(api_key=settings.groq_api_key)
        self.model = "llama-3.1-8b-instant"  # Faster model with higher rate limits
        
        # Simple in-memory document storage
        self.documents = []
        self.storage_file = os.path.join(settings.chroma_persist_dir, 'documents.json')
        
        # Search Index (BM25)
        self.inverted_index = defaultdict(list)
        self.doc_lengths = {}
        self.avg_doc_length = 0
        self.executor = ThreadPoolExecutor(max_workers=1)  # For non-blocking search
        
        # Load existing documents and build index
        self._load_documents()
    
    def _load_documents(self):
        """Load documents from JSON file and build search index."""
        if os.path.exists(self.storage_file):
            try:
                with open(self.storage_file, 'r', encoding='utf-8') as f:
                    self.documents = json.load(f)
                self._build_index()
            except:
                self.documents = []
                self.inverted_index = defaultdict(list)

    def _save_documents(self):
        """Save documents to JSON file."""
        os.makedirs(os.path.dirname(self.storage_file), exist_ok=True)
        with open(self.storage_file, 'w', encoding='utf-8') as f:
            json.dump(self.documents, f, ensure_ascii=False, indent=2)

    def _tokenize(self, text: str) -> List[str]:
        """Convert text to a list of lowercase tokens, removing punctuation."""
        # Simple tokenization: lowercase and remove non-alphanumeric chars
        text = text.lower()
        # Keep dots and hyphens for things like "3.5" or "co-op", remove others
        text = re.sub(r'[^\w\s\.-]', '', text)
        return text.split()

    def _build_index(self):
        """Build Inverted Index and calculate BM25 statistics."""
        self.inverted_index = defaultdict(list)
        self.doc_lengths = {}
        total_length = 0
        
        for idx, doc in enumerate(self.documents):
            text = doc.get('text', '')
            tokens = self._tokenize(text)
            length = len(tokens)
            self.doc_lengths[idx] = length
            total_length += length
            
            # Count term frequencies for this document
            term_counts = Counter(tokens)
            
            # Add to inverted index
            for term, count in term_counts.items():
                self.inverted_index[term].append((idx, count))
                
        self.avg_doc_length = total_length / len(self.documents) if self.documents else 0

    def add_documents(self, chunks: List[Dict[str, str]]) -> None:
        """Add document chunks to storage and update index."""
        if not chunks:
            return
        
        for chunk in chunks:
            self.documents.append({
                'text': chunk.get('text', ''),
                'source': chunk.get('source', 'unknown'),
                'page': chunk.get('page', 'N/A'),
                'chunk_id': chunk.get('chunk_id', '0')
            })
        
        self._save_documents()
        # Rebuild index (fast enough for small-medium datasets)
        self._build_index()

    def _calculate_bm25_scores(self, query: str, k1: float = 1.5, b: float = 0.75) -> List[tuple]:
        """
        Calculate BM25 scores for documents matching the query.
        Returns list of (score, doc_index) tuples.
        """
        query_tokens = self._tokenize(query)
        scores = defaultdict(float)
        
        if not self.documents:
            return []

        N = len(self.documents)
        
        for term in query_tokens:
            if term not in self.inverted_index:
                continue
            
            # Get list of documents containing this term
            postings = self.inverted_index[term]
            doc_freq = len(postings)
            
            # Calculate IDF
            idf = math.log((N - doc_freq + 0.5) / (doc_freq + 0.5) + 1)
            
            for doc_idx, term_freq in postings:
                doc_len = self.doc_lengths[doc_idx]
                
                # Calculate BM25 term score
                numerator = term_freq * (k1 + 1)
                denominator = term_freq + k1 * (1 - b + b * (doc_len / self.avg_doc_length))
                scores[doc_idx] += idf * (numerator / denominator)
                
        return sorted(scores.items(), key=lambda x: x[1], reverse=True)
    
    def _calculate_relevance_score(self, query: str, doc_text: str, weight: float = 1.0) -> float:
        """Calculate relevance score using a weighted keyword approach with fuzzy matching."""
        import re
        # Remove punctuation (except . and -) from query for better matching
        clean_query = re.sub(r'[^\w\s\.-]', '', query.lower())
        text_lower = doc_text.lower()
        
        # 1. Exact phrase match (High weight)
        score = 0.0
        if clean_query in text_lower:
            score += 15.0 * weight  # Boosted from 10.0
            
        # 2. Split into keywords (remove common stop words roughly)
        stop_words = {'what', 'is', 'the', 'how', 'to', 'in', 'of', 'for', 'a', 'an', 'at', 'on', 'does', 'do', 'can', 'i', 'we', 'it', 'its', 'that', 'this'}
        keywords = [k for k in clean_query.split() if k not in stop_words and len(k) > 2]
        
        if not keywords:
            return 0.0
            
        matches = 0
        text_words = text_lower.split()
        
        for keyword in keywords:
            # A. Direct substring match (Fast)
            if keyword in text_lower:
                matches += 1
                count = text_lower.count(keyword)
                score += (1.0 + min(count * 0.2, 1.0)) * weight
            
            # B. Fuzzy match (Slower, but catches typos/variations)
            else:
                # Check for words that are >= 75% similar
                close_matches = difflib.get_close_matches(keyword, text_words, n=1, cutoff=0.75)
                if close_matches:
                    matches += 0.8  # Slightly lower score for fuzzy match
                    score += 0.8 * weight
                
        # 3. Keyword density / coverage
        if matches > 0:
            coverage = matches / len(keywords)
            score += (coverage * 8.0) * weight  # Boosted from 5.0
            
        return score

    async def query_stream(self, question: str, n_results: int = 5) -> AsyncGenerator[Dict, None]:
        """Query the RAG system and stream the answer asynchronously."""
        
        if not self.documents:
            yield {
                'type': 'error',
                'message': "I don't have any documents uploaded yet. Please upload college documents through the Admin panel to get started!"
            }
            return

        # 1. Preprocess and Expand query
        processed_query = self._preprocess_query(question)
        expanded_queries = self._expand_query(processed_query)
        
        # Score documents
        doc_scores = []
        for doc in self.documents:
            score = 0
            
            # Score processed query (High weight)
            score += self._calculate_relevance_score(processed_query, doc['text'], weight=1.0)
            
            # Score expanded queries (Lower weight)
            for q in expanded_queries:
                score += self._calculate_relevance_score(q, doc['text'], weight=0.25)
            
            if score > 0:
                doc_scores.append((score, doc))
        
        # Sort by score
        doc_scores.sort(key=lambda x: x[0], reverse=True)
        
        # Take top N
        top_docs = [d[1] for d in doc_scores[:n_results]]
        
        # 3. Build Context
        context_parts = []
        if top_docs:
            for i, doc in enumerate(top_docs, 1):
                text = doc.get('text', '').strip()
                context_parts.append(f"{text}")
            context_str = "\n\n".join(context_parts)
        else:
            context_str = "No specific documents found matching the query."

        # 4. Receptionist System Prompt
        system_prompt = """You are Sarah, the friendly and professional Receptionist at the college.
Your goal is to assist students and parents with information about the college using the provided CONTEXT.

GUIDELINES:
1.  **Be Warm and Human**: Use natural, conversational language. Avoid robotic phrasing.
2.  **Use Context First**: Answer questions based on the provided CONTEXT.
3.  **Handle Missing Info**: If the answer is NOT in the context:
    *   Politely apologize.
    *   Say something like "I don't have that specific information right here."
    *   Suggest contacting the administration office for the most up-to-date details.
    *   DO NOT make up specific facts, dates, or fees.
4.  **Small Talk is Okay**: If the user greets you (e.g., "Hi", "How are you"), respond warmly without needing context.
5.  **Spoken Format**: Keep answers concise (under 3-4 sentences) and easy to listen to. Avoid bullet points or complex formatting.
6.  **No Citations**: DO NOT mention "Document X", "Source", or "Context" in your response. Just provide the answer naturally as if you know it.

Remember: You represent the college, so be helpful, polite, and welcoming!"""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"CONTEXT:\n{context_str}\n\nQUESTION: {question}"}
        ]

        # 5. Call Groq
        try:
            stream = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.7,  # Higher temperature for more natural conversation
                max_tokens=300,
                stream=True
            )

            # Yield metadata first
            yield {
                'type': 'meta',
                'sources': list(set(d.get('source', 'Unknown') for d in top_docs)),
                'context': [d.get('text', '') for d in top_docs],
                'language': 'en-US'
            }

            for chunk in stream:
                if chunk.choices[0].delta.content:
                    yield {'type': 'chunk', 'text': chunk.choices[0].delta.content}

        except Exception as e:
            print(f"Error calling Groq: {e}")
            yield {'type': 'error', 'message': "I'm having trouble connecting to my brain right now."}

    def _preprocess_query(self, query: str) -> str:
        """
        Clean and normalize user query to handle STT errors and domain specifics.
        """
        # 1. Basic cleaning
        query = query.lower().strip()
        
        # 2. Fix STT common misinterpretations for "AIML"
        # "aiemail", "a i m l", "ai ml", "aim l" -> "AIML"
        aiml_patterns = [r'\baiemail\b', r'\ba\s?i\s?m\s?l\b', r'\bai\s+ml\b']
        for pattern in aiml_patterns:
            query = re.sub(pattern, 'aiml', query)

        # 3. Handle "IT" vs "it" ambiguity
        # "it" implies Information Technology ONLY when associated with academic terms.
        
        # Pattern 1: "IT Department", "IT Branch"
        # Match: (it/i.t.) + space + (dept/branch/etc)
        pattern1 = r'\b(it|i\.t\.)\s+(department|dept|branch|course|engineering|field|sector|program|major)\b'
        query = re.sub(pattern1, lambda m: f"information technology {m.group(2)}", query)

        # Pattern 2: "BTech in IT", "Master of IT"
        # Match: (degree) + space + (in/of)? + space + (it/i.t.)
        pattern2 = r'\b(btech|b\.tech|mtech|m\.tech|degree|diploma|bachelor|master)\s+(in|of)?\s*(it|i\.t\.)\b'
        query = re.sub(pattern2, lambda m: f"{m.group(1)} {m.group(2) + ' ' if m.group(2) else ''}information technology", query)
            
        return query

    def _expand_query(self, query: str) -> List[str]:
        """Simple keyword expansion."""
        # This is a basic implementation. In production, use an LLM to generate synonyms.
        import re
        # Remove punctuation for better matching
        clean_query = re.sub(r'[^\w\s]', '', query.lower())
        keywords = clean_query.split()
        expanded = []
        
        # Common college synonyms map
        synonyms = {
            "fee": ["tuition", "cost", "price", "payment", "dues", "charges", "amount"],
            "course": ["program", "degree", "subject", "major", "stream", "branch", "specialization", "curriculum"],
            "location": ["address", "where", "place", "campus", "located", "situated", "map", "directions"],
            "contact": ["email", "phone", "number", "reach", "call", "helpline", "support", "office"],
            "admission": ["apply", "application", "entry", "requirements", "eligibility", "process", "enrollment", "criteria"],
            "faculty": ["teacher", "professor", "staff", "mentor", "guide", "hod", "principal", "director"],
            "placement": ["job", "career", "salary", "package", "recruiter", "company", "hiring", "opportunities"],
            "hostel": ["accommodation", "stay", "room", "living", "boarding", "residence", "mess"],
            "exam": ["test", "schedule", "routine", "date", "marks", "grade", "result", "semester"],
            "scholarship": ["financial aid", "grant", "support", "funding", "discount", "waiver"]
        }
        
        for word in keywords:
            if word in synonyms:
                expanded.extend(synonyms[word])
            
            # Reverse lookup: if user asks "cost", finding "fee" is helpful
            for key, values in synonyms.items():
                if word in values:
                    expanded.append(key)
        
        return list(set(expanded))  # Unique values

    async def query(self, question: str, n_results: int = 5) -> Dict[str, any]:
        """Query the RAG system and return answer with sources (Async)."""
        
        full_answer = ""
        sources = []
        context = []
        language = "en-US"
        
        try:
            async for chunk in self.query_stream(question, n_results):
                if chunk['type'] == 'meta':
                    sources = chunk['sources']
                    context = chunk['context']
                    language = chunk['language']
                elif chunk['type'] == 'chunk':
                    full_answer += chunk['text']
                elif chunk['type'] == 'error':
                     return {
                         'answer': chunk['message'], 
                         'sources': [], 
                         'context': [], 
                         'language': 'en-US'
                     }
        except Exception as e:
            return {
                'answer': f"Error: {str(e)}", 
                'sources': [], 
                'context': [], 
                'language': 'en-US'
            }

        return {
            'answer': full_answer,
            'sources': sources,
            'context': context,
            'language': language
        }
    
    def delete_all_documents(self) -> None:
        """Delete all documents."""
        self.documents = []
        self._save_documents()
        self._build_index()
    
    def delete_documents_by_source(self, filename: str) -> int:
        """Delete all documents from a specific source file.
        
        Args:
            filename: The filename to delete documents for
            
        Returns:
            Number of documents deleted
        """
        initial_count = len(self.documents)
        self.documents = [doc for doc in self.documents if doc.get('source') != filename]
        deleted_count = initial_count - len(self.documents)
        
        if deleted_count > 0:
            self._save_documents()
            self._build_index()
        
        return deleted_count
    
    def get_document_count(self) -> int:
        """Get total number of documents."""
        return len(self.documents)
    
    def check_groq_connection(self) -> bool:
        """Check if Groq API is accessible."""
        try:
            # Test Groq connection with a simple request
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": "test"}],
                max_tokens=5
            )
            return True
        except Exception:
            return False
