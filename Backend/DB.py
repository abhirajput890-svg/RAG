import psycopg2
from typing import List, Optional, Dict, Any
import os
from dotenv import load_dotenv
import logging

logger = logging.getLogger(__name__)

load_dotenv()

POSTGRES_DSN = os.getenv("POSTGRES_DSN")
POSTGRES = os.getenv("POSTGRES")

class DocumentDB:
    """PostgreSQL DB interface for documents with improved error handling."""

    def __init__(self, dsn: str = POSTGRES):
        self.dsn = dsn
        if not self.dsn:
            raise ValueError("Database DSN not provided")
        logger.info("Initialized DocumentDB")

    def test_connection(self) -> bool:
        """Test database connection"""
        try:
            with psycopg2.connect(self.dsn) as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT 1")
                    return True
        except Exception as e:
            logger.error(f"Database connection failed: {str(e)}")
            return False

    def fetch_documents(self) -> List[str]:
        """Fetch all documents from the database with improved error handling"""
        try:
            with psycopg2.connect(self.dsn) as conn:
                with conn.cursor() as cur:
                    # First, check what tables exist
                    cur.execute("""
                        SELECT table_name 
                        FROM information_schema.tables 
                        WHERE table_schema = 'public'
                    """)
                    tables = cur.fetchall()
                    logger.info(f"Available tables: {[t[0] for t in tables]}")
                    
                    # Try to fetch documents - adjust this query based on your actual table structure
                    try:
                        cur.execute("SELECT doc_text FROM documents WHERE doc_text IS NOT NULL AND doc_text != ''")
                        rows = cur.fetchall()
                        documents = [row[0].strip() for row in rows if row[0] and row[0].strip()]

                        logger.info(f"Fetched {len(documents)} valid documents from database")
                        
                        if documents:
                            logger.info(f"Sample documents: {documents[:2]}")
                        else:
                            logger.warning("No documents found in database")
                            
                        return documents
                        
                    except psycopg2.Error as e:
                        # If 'content' column doesn't exist, try other common column names
                        logger.warning(f"Failed to fetch with 'content' column: {e}")
                        
                        # Try different column names
                        for col_name in ['text', 'documents', 'doc_text', 'body']:
                            try:
                                cur.execute(f"SELECT {col_name} FROM documents WHERE {col_name} IS NOT NULL AND {col_name} != ''")
                                rows = cur.fetchall()
                                documents = [row[0].strip() for row in rows if row[0] and row[0].strip()]
                                logger.info(f"Successfully fetched {len(documents)} documents using column '{col_name}'")
                                return documents
                            except psycopg2.Error:
                                continue
                        
                        # If all else fails, try to get column information
                        cur.execute("""
                            SELECT column_name, data_type 
                            FROM information_schema.columns 
                            WHERE table_name = 'documents'
                        """)
                        columns = cur.fetchall()
                        logger.error(f"Available columns in 'documents' table: {columns}")
                        raise Exception(f"Could not find a suitable text column in documents table. Available columns: {columns}")
                        
        except Exception as e:
            logger.error(f"Error fetching documents: {str(e)}")
            # Return some sample documents for testing if DB fails
            return self._get_sample_documents()
        
    def _get_sample_documents(self) -> List[str]:
        """Return sample documents for testing when DB is unavailable"""
        logger.warning("Using sample documents due to database connection issues")
        return [
            "Python is a high-level programming language known for its simplicity and readability.",
            "Machine learning is a subset of artificial intelligence that focuses on algorithms that can learn from data.",
            "FastAPI is a modern, fast web framework for building APIs with Python.",
            "Natural Language Processing (NLP) is a field of AI that focuses on the interaction between computers and human language.",
            "Vector databases are specialized databases designed to store and query high-dimensional vectors efficiently.",
            "Retrieval Augmented Generation (RAG) combines retrieval systems with language models to provide more accurate responses.",
            "FAISS is a library for efficient similarity search and clustering of dense vectors.",
            "Sentence transformers are neural networks that map sentences to dense vector representations.",
        ]


    def add_document(self, content: str) -> bool:
        """Add a new document to the database"""
        if not content or not content.strip():
            logger.warning("Cannot add empty document")
            return False
            
        try:
            with psycopg2.connect(self.dsn) as conn:
                with conn.cursor() as cur:
                    cur.execute("INSERT INTO documents (content) VALUES (%s)", (content.strip(),))
                    conn.commit()
                    logger.info("Successfully added new document")
                    return True
        except Exception as e:
            logger.error(f"Error adding document: {str(e)}")
            return False

    def get_document_count(self) -> int:
        """Get the total number of documents in the database"""
        try:
            with psycopg2.connect(self.dsn) as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT COUNT(*) FROM documents")
                    count = cur.fetchone()[0]
                    logger.info(f"Total documents in database: {count}")
                    return count
        except Exception as e:
            logger.error(f"Error getting document count: {str(e)}")
            return 0

class AuthDB:
    """PostgreSQL DB interface for user authentication with improved error handling."""

    def __init__(self, dsn: str = POSTGRES_DSN):
        self.dsn = dsn
        if not self.dsn:
            raise ValueError("Auth database DSN not provided")
        logger.info("Initialized AuthDB")

    def test_connection(self) -> bool:
        """Test database connection"""
        try:
            with psycopg2.connect(self.dsn) as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT 1")
                    return True
        except Exception as e:
            logger.error(f"Auth database connection failed: {str(e)}")
            return False

    def get_user(self, username: str) -> Optional[Dict[str, Any]]:
        """Get user information with improved error handling"""
        if not username:
            return None
            
        try:
            with psycopg2.connect(self.dsn) as conn:
                with conn.cursor() as cur:
                    # Fix the extra space in password_hash column name
                    cur.execute("SELECT username, password_hash FROM users WHERE username = %s", (username,))
                    row = cur.fetchone()
                    if row:
                        logger.info(f"User '{username}' found in database")
                        return {"username": row[0], "password_hash": row[1]}  # Fixed key name
                    else:
                        logger.warning(f"User '{username}' not found in database")
                        return None
        except Exception as e:
            logger.error(f"Error fetching user '{username}': {str(e)}")
            return None