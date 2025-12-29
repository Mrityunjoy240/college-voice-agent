import json
import numpy as np
import time
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from collections import defaultdict
from pathlib import Path
import logging

from rank_bm25 import BM25Okapi
from sentence_transformers import SentenceTransformer
import asyncio

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ============================================================================
# 1. HYBRID RETRIEVER - BM25 + Semantic Similarity
# ============================================================================

class HybridRetriever:
    """
    Combines BM25 lexical matching with semantic similarity for robust retrieval.
    Handles both keyword-based and paraphrased queries effectively.
    """
    
    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        """
        Initialize the hybrid retriever.
        
        Args:
            model_name: SentenceTransformer model (lightweight, ~33MB)
        """
        self.encoder = SentenceTransformer(model_name)
        self.bm25 = None
        self.documents = []
        self.embeddings = None
        self.embedding_cache = {}
        logger.info(f"Initialized HybridRetriever with {model_name}")
    
    def index_documents(self, documents: List[Dict]) -> None:
        """
        Index documents once at startup. Embeddings computed once and cached.
        
        Args:
            documents: List of dicts with 'content', 'source', 'metadata'
        
        Example:
            documents = [
                {'content': 'CS branch offers...', 'source': 'programs.json', 'metadata': {'year': 2024}},
                {'content': 'Admission deadline...', 'source': 'admissions.json', 'metadata': {}},
            ]
        """
        self.documents = documents
        logger.info(f"Indexing {len(documents)} documents...")
        
        # Build BM25 index
        tokenized_docs = [
            doc['text'].lower().split() 
            for doc in documents
        ]
        self.bm25 = BM25Okapi(tokenized_docs)
        
        # Compute embeddings in batch (one-time cost)
        contents = [doc['text'] for doc in documents]
        start_time = time.time()
        self.embeddings = self.encoder.encode(
            contents, 
            batch_size=32,
            show_progress_bar=False,
            convert_to_numpy=True
        )
        embed_time = time.time() - start_time
        
        logger.info(f"Indexed {len(documents)} documents in {embed_time:.2f}s")
        logger.info(f"Embedding shape: {self.embeddings.shape}")
    
    def _normalize_scores(self, scores: np.ndarray) -> np.ndarray:
        """Min-max normalization to [0, 1]"""
        min_score = scores.min()
        max_score = scores.max()
        
        if max_score == min_score:
            return np.ones_like(scores) * 0.5
        
        return (scores - min_score) / (max_score - min_score)
    
    def retrieve(
        self, 
        query: str, 
        k: int = 5,
        bm25_weight: float = 0.4,
        semantic_weight: float = 0.6
    ) -> List[Dict]:
        """
        Hybrid retrieval combining BM25 and semantic similarity.
        
        Args:
            query: User query
            k: Number of documents to retrieve
            bm25_weight: Weight for lexical matching (0-1)
            semantic_weight: Weight for semantic similarity (0-1)
        
        Returns:
            List of top-k documents with scores
        """
        
        if not self.bm25 or self.embeddings is None:
            raise ValueError("Documents not indexed. Call index_documents() first.")
        
        # BM25 scores
        bm25_scores = self.bm25.get_scores(query.lower().split())
        bm25_normalized = self._normalize_scores(bm25_scores)
        
        # Semantic similarity via cosine distance
        query_embedding = self.encoder.encode(query, convert_to_numpy=True)
        
        # Cosine similarity: dot product of normalized vectors
        embedding_norms = np.linalg.norm(self.embeddings, axis=1, keepdims=True)
        query_norm = np.linalg.norm(query_embedding)
        
        semantic_scores = np.dot(
            self.embeddings / (embedding_norms + 1e-10),
            query_embedding / (query_norm + 1e-10)
        )
        semantic_normalized = self._normalize_scores(semantic_scores)
        
        # Hybrid score: weighted combination
        hybrid_scores = (
            bm25_weight * bm25_normalized + 
            semantic_weight * semantic_normalized
        )
        
        # Get top-k indices
        top_indices = np.argsort(hybrid_scores)[::-1][:k]
        
        results = [
            {
                'document': self.documents[i],
                'hybrid_score': float(hybrid_scores[i]),
                'bm25_score': float(bm25_normalized[i]),
                'semantic_score': float(semantic_normalized[i]),
                'rank': rank + 1
            }
            for rank, i in enumerate(top_indices)
        ]
        
        return results


# ============================================================================
# 2. QUERY EXPANSION - Context-Aware Query Enhancement
# ============================================================================

class QueryExpander:
    """
    Expands short/ambiguous queries using conversation history.
    Reduces need for clarification in multi-turn conversations.
    """
    
    def __init__(self, llm_client):
        """
        Args:
            llm_client: Groq client or similar (must have invoke() method)
        """
        self.llm = llm_client
        self.session_history = defaultdict(list)
    
    def add_to_history(self, session_id: str, query: str) -> None:
        """Track query history per session"""
        self.session_history[session_id].append(query)
        
        # Keep only last 5 queries to avoid token bloat
        if len(self.session_history[session_id]) > 5:
            self.session_history[session_id].pop(0)
    
    def _should_expand(self, query: str, history: List[str]) -> bool:
        """
        Heuristic: expand if query is short AND history exists
        Avoids unnecessary API calls on clear queries.
        """
        is_short = len(query.split()) < 4
        has_history = len(history) > 0
        
        return is_short and has_history
    
    async def expand_query(
        self, 
        query: str, 
        session_id: str
    ) -> Tuple[str, bool]:
        """
        Expand ambiguous query with context.
        
        Args:
            query: Original user query
            session_id: Conversation session ID
        
        Returns:
            (expanded_query, was_expanded)
        """
        
        history = self.session_history[session_id]
        
        if not self._should_expand(query, history):
            return query, False
        
        # Build expansion prompt
        history_str = " -> ".join(history[-3:]) if history else ""
        expansion_prompt = f"""Given the conversation context, expand this ambiguous query to be more specific and complete.

Context: {history_str}
Current query: "{query}"

Rules:
- Keep it concise (under 20 words)
- Infer topic from history if needed
- Return ONLY the expanded query, nothing else"""

        try:
            # Call Groq API with minimal overhead
            response = self.llm.chat.completions.create(
                messages=[{"role": "user", "content": expansion_prompt}],
                model="llama3-8b-8192",  # Using Groq model
                temperature=0,
                max_tokens=20
            )
            expanded = response.choices[0].message.content.strip()
            
            logger.info(f"Query expansion: '{query}' -> '{expanded}'")
            return expanded, True
            
        except Exception as e:
            logger.warning(f"Query expansion failed: {e}. Using original query.")
            return query, False


# ============================================================================
# 3. SYSTEM PROMPT - College-Specific Instructions
# ============================================================================

class SystemPromptBuilder:
    """
    Builds college-specific system prompts that reduce hallucination.
    """
    
    def __init__(self, college_config: Dict):
        """
        Args:
            college_config: Dict with college name, departments, contact info
        
        Example:
            {
                'name': 'Tech Institute',
                'support_email': 'support@tech.edu',
                'admissions_phone': '+91-9999-9999',
                'departments': ['CS', 'EC', 'ME']
            }
        """
        self.config = college_config
    
    def build_system_prompt(self, retrieved_context: List[Dict]) -> str:
        """
        Build system prompt with retrieved context.
        
        Args:
            retrieved_context: List of retrieved documents with scores
        
        Returns:
            Full system prompt with instructions and context
        """
        
        # Format context from retrieved documents
        context_blocks = []
        for doc in retrieved_context:
            source = doc['document'].get('source', 'Unknown')
            content = doc['document'].get('text', '')
            score = doc['hybrid_score']
            
            context_blocks.append(
                f"[{source}] (confidence: {score:.2f})\n{content}"
            )
        
        context_str = "\n\n".join(context_blocks)
        
        system_prompt = f"""You are an automated calling agent for {self.config['name']}.

Your role is to provide accurate information about:
- Academic programs (branches, specializations, eligibility)
- Admission process (deadlines, documents, fees)
- Campus facilities (hostel, labs, library, medical)
- Policies (attendance, dress code, conduct)
- Department details and contact information

CRITICAL RULES:
1. ONLY answer based on provided documents. Do NOT use general knowledge about colleges.
2. If information is not in documents, respond: "I don't have that information. Please contact {self.config['name']} Admissions at {self.config.get('admissions_phone', 'admissions office')}"
3. For multi-part questions, address each part separately if found in different documents.
4. Always provide relevant department contact details when mentioning services.
5. For time-sensitive info (fees, deadlines), include: "This information is current as of the last update. Please verify with admissions."

TONE: Professional, helpful, concise (1-2 sentences per answer)

---CONTEXT FROM COLLEGE DOCUMENTS---

{context_str}

---END CONTEXT---

Remember: Answer only what's in the documents above."""
        
        return system_prompt


# ============================================================================
# 4. QUERY ANALYTICS - Monitoring & Quality Tracking
# ============================================================================

class QueryAnalytics:
    """
    Tracks query performance, retrieval quality, and latency.
    Identifies problematic queries for document updates.
    """
    
    def __init__(self, output_dir: str = "./analytics"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        
        self.metrics = defaultdict(list)
    
    def log_interaction(self, session_id: str, query: str, retrieved_docs: List[Dict], 
                       response: str, latency: float) -> None:
        """Log every interaction for analysis"""
        
        self.metrics['interactions'].append({
            'timestamp': datetime.utcnow().isoformat(),
            'session_id': session_id,
            'query': query,
            'retrieval_score': retrieved_docs[0]['hybrid_score'] if retrieved_docs else 0,
            'response_length': len(response),
            'latency_ms': latency * 1000
        })
    
    def get_quality_report(self) -> Dict:
        """Generate quality metrics"""
        interactions = self.metrics['interactions']
        
        if not interactions:
            return {'error': 'No interactions logged yet'}
        
        return {
            'total_queries': len(interactions),
            'avg_latency_ms': np.mean([i['latency_ms'] for i in interactions]),
            'retrieval_confidence': np.mean([i['retrieval_score'] for i in interactions]),
            'low_confidence_queries': [
                i for i in interactions 
                if i['retrieval_score'] < 0.3
            ]
        }


# ============================================================================
# 5. MAIN RAG SERVICE - Integration of All Components
# ============================================================================

class RAGService:
    """
    Main RAG service integrating hybrid retrieval, query expansion, and analytics.
    """
    
    def __init__(self):
        self.hybrid_retriever = HybridRetriever()
        self.query_expander = None  # Will be set after initialization
        self.system_prompt_builder = None  # Will be set after initialization
        self.analytics = QueryAnalytics()
        
        # Load documents from JSON file
        self.documents = self._load_documents()
        
        # Index documents for retrieval
        if self.documents:
            self.hybrid_retriever.index_documents(self.documents)
        
        logger.info(f"RAGService initialized with {len(self.documents)} documents")
    
    def _load_documents(self) -> List[Dict]:
        """Load documents from JSON file"""
        try:
            storage_file = Path("chroma_db/documents.json")
            if storage_file.exists():
                with open(storage_file, 'r', encoding='utf-8') as f:
                    documents = json.load(f)
                    logger.info(f"Loaded {len(documents)} documents from {storage_file}")
                    return documents
            else:
                logger.warning(f"Documents file {storage_file} not found")
                return []
        except Exception as e:
            logger.error(f"Error loading documents: {e}")
            return []
    
    def set_clients(self, llm_client, college_config: Dict):
        """Set LLM client and college config after initialization"""
        self.query_expander = QueryExpander(llm_client)
        self.system_prompt_builder = SystemPromptBuilder(college_config)
    
    async def query_stream(self, message: str, session_id: str = None):
        """
        Main query method that integrates all components.
        """
        start_time = time.time()
        
        try:
            # Expand query if needed
            if self.query_expander:
                expanded_query, was_expanded = await self.query_expander.expand_query(
                    message, session_id or "default"
                )
                query_to_use = expanded_query if was_expanded else message
            else:
                query_to_use = message
            
            # Retrieve relevant documents
            retrieved_docs = self.hybrid_retriever.retrieve(query_to_use, k=5)
            
            # Build system prompt with context
            if self.system_prompt_builder:
                system_prompt = self.system_prompt_builder.build_system_prompt(retrieved_docs)
            else:
                # Fallback prompt
                context_str = "\n\n".join([doc['document']['text'] for doc in retrieved_docs])
                system_prompt = f"""You are a college information assistant. Answer based on the following context:\n\n{context_str}"""
            
            # Log the interaction
            latency = time.time() - start_time
            if self.analytics:
                self.analytics.log_interaction(
                    session_id or "default", 
                    message, 
                    retrieved_docs, 
                    "response_placeholder", 
                    latency
                )
            
            # Yield the results
            yield {
                "type": "documents",
                "documents": retrieved_docs,
                "query_used": query_to_use,
                "processing_time": latency
            }
            
        except Exception as e:
            logger.error(f"Error in query_stream: {e}")
            yield {
                "type": "error",
                "message": str(e)
            }
    
    def get_document_count(self):
        """Get total number of indexed documents"""
        return len(self.documents)
    
    def check_groq_connection(self):
        """Check if Groq connection is working"""
        # This is a simplified check - in real implementation you'd test the actual connection
        return True  # Placeholder - implement actual connection check
