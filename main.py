import numpy as np
from sentence_transformers import SentenceTransformer
import faiss
import os
from typing import List, Tuple, Optional
from dotenv import load_dotenv
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

# Initialize OpenAI client (updated for newer versions)
from openai import OpenAI
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Load model globally
model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")

class VectorIndex:
    def search(self, query_embedding: np.ndarray, k: int) -> Tuple[np.ndarray, np.ndarray]:
        raise NotImplementedError

    def build(self, embeddings: np.ndarray):
        raise NotImplementedError

class FaissIndex(VectorIndex):
    def __init__(self, dim: int):
        self.dim = dim
        self.index = faiss.IndexFlatL2(dim)
        self.embeddings = None
        logger.info(f"Initialized FAISS index with dimension: {dim}")

    def build(self, embeddings: np.ndarray):
        """Build the FAISS index with embeddings"""
        if embeddings.size == 0:
            logger.error("Cannot build index: embeddings array is empty")
            return
        
        # Ensure proper shape
        if embeddings.ndim == 1:
            embeddings = embeddings.reshape(1, -1)
        
        # Validate dimensions
        if embeddings.shape[1] != self.dim:
            logger.error(f"Embedding dimension mismatch. Expected {self.dim}, got {embeddings.shape[1]}")
            return
            
        self.embeddings = embeddings.astype('float32')
        self.index.reset()
        self.index.add(self.embeddings)
        logger.info(f"Built FAISS index with {embeddings.shape[0]} documents, dimension {embeddings.shape[1]}")

    def search(self, query_embedding: np.ndarray, k: int) -> Tuple[np.ndarray, np.ndarray]:
        """Search for k nearest neighbors"""
        if self.index.ntotal == 0:
            logger.error("Index is empty - no documents to search")
            return np.array([[float('inf')]]), np.array([[0]])
        
        # Ensure proper shape for query
        if query_embedding.ndim == 1:
            query_embedding = query_embedding.reshape(1, -1)
            
        query_embedding = query_embedding.astype('float32')
        
        # Limit k to available documents
        k = min(k, self.index.ntotal)
        
        distances, indices = self.index.search(query_embedding, k)
        logger.debug(f"Search results - Distances: {distances[0][:3]}, Indices: {indices[0][:3]}")
        return distances, indices

class RAGChatbot:
    def __init__(self, docs: List[str], model: SentenceTransformer, index: Optional[VectorIndex] = None):
        # Filter out empty documents and ensure all are strings
        self.docs = [str(doc).strip() for doc in docs if doc and str(doc).strip()]
        
        if not self.docs:
            logger.error("No valid documents provided to RAGChatbot")
            raise ValueError("No valid documents provided")
            
        logger.info(f"Initialized RAGChatbot with {len(self.docs)} documents")
        
        self.model = model
        self.index = index
        self._build_index()

    def _build_index(self):
        """Build the vector index from documents"""
        logger.info("Building embeddings for documents...")
        
        # Create embeddings for all documents
        embeddings = self.model.encode(self.docs, convert_to_numpy=True, show_progress_bar=True)
        embeddings = embeddings.astype("float32")
        
        if embeddings.ndim == 1:
            embeddings = embeddings.reshape(1, -1)

        dim = embeddings.shape[1]
        logger.info(f"Generated embeddings with shape: {embeddings.shape}")
        
        # Create FAISS index if not provided
        if self.index is None:
            self.index = FaissIndex(dim)
        
        self.index.build(embeddings)

    def call_rag(self, q: str, indices: np.ndarray, distances: np.ndarray) -> str:
            """Generate response using retrieved documents"""
            try:
                # Only keep top 1 or 2 docs (implement top_k filtering)
                top_k = 2  # or set top_k = 1 for max focus
                valid_indices = [
                    idx for i, idx in enumerate(indices[0][:top_k]) if idx < len(self.docs)
                ]
                retrieved_docs = [
                    f"{self.docs[idx]}" for idx in valid_indices
                ]
                if not retrieved_docs:
                    logger.warning("No valid documents retrieved for RAG")
                    return self.fallback(q)

                # Join only the most relevant documents
                context = "\n\n".join(retrieved_docs)
                logger.info(f"Using RAG with {len(retrieved_docs)} retrieved documents")
                logger.info(f"Context sent to OpenAI: {repr(context[:300])}")  # Print first 300 chars for debugging

                prompt = f"""Answer the question based only on the context below.
        If the context doesn't contain information to answer the question,
        say "I don't have enough information in the provided context to answer this question."


        Context:
        {context}


        Question: {q}

        Answer:"""

                response = client.chat.completions.create(
                    model="gpt-4",
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.1,
                    max_tokens=500
                )

                answer = response.choices[0].message.content.strip()
                logger.info("RAG response generated successfully")
                return answer

            except Exception as e:
                logger.error(f"Error in call_rag: {str(e)}")
                return self.fallback(q)


    def fallback(self, q: str) -> str:
        """Generate response without retrieved context"""
        try:
            logger.info("Using fallback (no retrieved context)")
            prompt = f"""Answer the question as best as you can using your general knowledge.

                        Question: {q}

                        Answer:"""

            response = client.chat.completions.create(
                model="gpt-4",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7,
                max_tokens=500
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            logger.error(f"Error in fallback: {str(e)}")
            return f"Sorry, I encountered an error: {str(e)}"

    def query(self, q: str, threshold: float = 1.0, k: int = 3) -> str:
        """Query the chatbot with adaptive thresholding"""
        if not q or not q.strip():
            return "Please provide a valid question."
            
        try:
            # Generate query embedding
            q_embd = self.model.encode([q], convert_to_numpy=True).astype("float32")
            
            # Search for similar documents
            distances, indices = self.index.search(q_embd, k=k)
            
            # Log search results for debugging
            logger.info(f"Query: '{q}'")
            logger.info(f"Best match distance: {distances[0][0]:.3f}")
            logger.info(f"Threshold: {threshold}")
            
            # Check if we have valid results and if the best match is below threshold
            if (distances[0][0] < threshold):
                
                logger.info("Using RAG (retrieved context)")
                return self.call_rag(q, indices, distances)
            else:
                logger.info(f"Using fallback - Distance {distances[0][0]:.3f} > threshold {threshold}")
                return self.fallback(q)
                
        except Exception as e:
            logger.error(f"Error in query processing: {str(e)}")
            return self.fallback(q)

    def get_diagnostics(self) -> dict:
        """Get diagnostic information about the chatbot"""
        return {
            "num_documents": len(self.docs),
            "sample_documents": self.docs[:3] if self.docs else [],
            "index_total": self.index.index.ntotal if hasattr(self.index, 'index') else 0,
            "embedding_dim": self.index.dim if hasattr(self.index, 'dim') else None
        }