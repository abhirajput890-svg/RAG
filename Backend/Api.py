from fastapi import FastAPI, UploadFile, File, HTTPException, BackgroundTasks, Depends
from fastapi.responses import JSONResponse
from fastapi.security import OAuth2PasswordRequestForm, OAuth2PasswordBearer
from pydantic import BaseModel
from typing import List, Optional
import io
from PIL import Image
import pytesseract as pt
import cv2
import numpy as np
import imghdr
import jwt
import datetime
from passlib.context import CryptContext
import os
import logging
from dotenv import load_dotenv

load_dotenv()
# Import your modules
from DB import DocumentDB, AuthDB
from main import RAGChatbot, FaissIndex, model

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI(title="RAG Chatbot API", version="1.0.0")

# Environment variables
POSTGRES = os.getenv("POSTGRES")
POSTGRES_DSN = os.getenv("POSTGRES_DSN")
SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# CORS middleware
from fastapi.middleware.cors import CORSMiddleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global variables for initialization
chatbot: Optional[RAGChatbot] = None
doc_db: Optional[DocumentDB] = None
auth_db: Optional[AuthDB] = None

# Authentication Setup
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

def initialize_chatbot():
    """Initialize the chatbot with proper error handling"""
    global chatbot, doc_db, auth_db
    
    try:
        logger.info("Initializing RAG Chatbot...")
        
        # Initialize databases
        doc_db = DocumentDB(POSTGRES)
        auth_db = AuthDB(POSTGRES_DSN)
        
        # Test database connections
        if not doc_db.test_connection():
            logger.warning("Document database connection failed, using sample data")
        
        if not auth_db.test_connection():
            logger.warning("Auth database connection failed")
        
        # Fetch documents
        docs = doc_db.fetch_documents()
        logger.info(f"Fetched {len(docs)} documents from database")
        
        if not docs:
            logger.error("No documents available for RAG")
            raise Exception("No documents available")
        
        # Initialize FAISS index and chatbot
        faiss_index = FaissIndex(dim=384)  # all-MiniLM-L6-v2 dimension
        chatbot = RAGChatbot(docs, model, faiss_index)
        
        # Print diagnostics
        diagnostics = chatbot.get_diagnostics()
        logger.info(f"Chatbot diagnostics: {diagnostics}")
        
        logger.info("RAG Chatbot initialized successfully!")
        return True
        
    except Exception as e:
        logger.error(f"Failed to initialize chatbot: {str(e)}")
        return False

# Initialize on startup
@app.on_event("startup")
async def startup_event():
    success = initialize_chatbot()
    if not success:
        logger.error("Failed to initialize chatbot - some features may not work")

# Authentication functions
def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def authenticate_user(username: str, password: str):
    if not auth_db:
        return None
    user = auth_db.get_user(username)
    if not user or not verify_password(password, user["password_hash"]):  # Fixed key name
        return False
    return user

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.datetime.utcnow() + datetime.timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    token = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return token

async def get_current_user(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=401,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
        if not auth_db:
            raise credentials_exception
        user = auth_db.get_user(username)
        if user is None:
            raise credentials_exception
        return user
    except Exception as e:
        logger.error(f"Authentication error: {str(e)}")
        raise credentials_exception

# OCR Preprocessing
Allowed_image_type = {"jpeg", "png", "bmp", "tiff", "webp"}

def preprocessing_for_ocr(image: Image.Image) -> Image.Image:
    """Preprocess image for better OCR results"""
    cv_image = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
    grey = cv2.cvtColor(cv_image, cv2.COLOR_BGR2GRAY)
    thresh = cv2.adaptiveThreshold(
        grey, 255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY,
        11, 2
    )
    denoised = cv2.fastNlMeansDenoising(thresh, h=30)
    processed = Image.fromarray(denoised)
    return processed

async def ocr_and_query(image_bytes: bytes):
    """Extract text from image and query the chatbot"""
    if not chatbot:
        raise ValueError("Chatbot not initialized")
        
    image = Image.open(io.BytesIO(image_bytes))
    processed_image = preprocessing_for_ocr(image)

    text = pt.image_to_string(processed_image).strip()
    if not text:
        raise ValueError("No text detected in image")

    response = chatbot.query(text)
    return text, response

# Pydantic models
class QueryRequest(BaseModel):
    text: List[str]

class QueryResponse(BaseModel):
    text: List[str]
    results: List[str]

class SingleQueryRequest(BaseModel):
    question: str
    threshold: Optional[float] = 0.8

class DiagnosticsResponse(BaseModel):
    chatbot_status: str
    num_documents: int
    sample_documents: List[str]
    index_total: int
    embedding_dim: Optional[int]

# API Routes
@app.get("/")
async def root():
    return {
        "message": "RAG Chatbot API is running",
        "chatbot_initialized": chatbot is not None,
        "version": "1.0.0"
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    status = {
        "status": "healthy",
        "chatbot_initialized": chatbot is not None,
        "database_connected": doc_db.test_connection() if doc_db else False,
        "auth_database_connected": auth_db.test_connection() if auth_db else False
    }
    return status

@app.get("/diagnostics", response_model=DiagnosticsResponse)
async def get_diagnostics():
    """Get diagnostic information about the chatbot"""
    if not chatbot:
        raise HTTPException(status_code=503, detail="Chatbot not initialized")
    
    diagnostics = chatbot.get_diagnostics()
    return DiagnosticsResponse(
        chatbot_status="initialized",
        num_documents=diagnostics["num_documents"],
        sample_documents=diagnostics["sample_documents"],
        index_total=diagnostics["index_total"],
        embedding_dim=diagnostics["embedding_dim"]
    )

@app.post("/token")
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    user = authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(status_code=401, detail="Incorrect username or password")
    access_token = create_access_token({"sub": user["username"]})
    return {"access_token": access_token, "token_type": "bearer"}

@app.post("/query", response_model=QueryResponse)
async def query_texts(text_batch: QueryRequest, current_user: dict = Depends(get_current_user)):
    """Query multiple texts"""
    if not chatbot:
        raise HTTPException(status_code=503, detail="Chatbot not initialized")
    
    logger.info(f"User {current_user['username']} submitted batch query with {len(text_batch.text)} texts")
    
    try:
        results = []
        for text in text_batch.text:
            if text.strip():
                result = chatbot.query(text.strip())
                results.append(result)
            else:
                results.append("Empty query provided")
        
        logger.info(f"Batch query processing completed successfully")
        return QueryResponse(text=text_batch.text, results=results)
        
    except Exception as e:
        logger.error(f"Error processing batch query: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/file")
async def upload_image(
    background: BackgroundTasks, 
    file: UploadFile = File(...), 
    current_user: dict = Depends(get_current_user)
):
    """Upload and process an image file"""
    if not chatbot:
        raise HTTPException(status_code=503, detail="Chatbot not initialized")
        
    logger.info(f"User {current_user['username']} uploading file: {file.filename}")
    
    content = await file.read()
    if len(content) > 10 * 1024 * 1024:  # 10MB limit
        logger.warning(f"User {current_user['username']} uploaded file too large")
        raise HTTPException(status_code=413, detail="File too large (max 10MB)")

    kind = imghdr.what(None, h=content)
    if kind not in Allowed_image_type:
        logger.warning(f"User {current_user['username']} uploaded unsupported file type: {kind}")
        raise HTTPException(status_code=400, detail=f"Unsupported image type: {kind}")

    try:
        text, response = await ocr_and_query(content)
        logger.info(f"OCR and query successful for user {current_user['username']}")
        return JSONResponse({
            "filename": file.filename,
            "extracted_text": text,
            "response": response
        })
    except Exception as e:
        logger.error(f"OCR/query error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/batch_files")
async def upload_multiple_images(
    files: List[UploadFile] = File(...), 
    current_user: dict = Depends(get_current_user)
):
    """Upload and process multiple image files"""
    if not chatbot:
        raise HTTPException(status_code=503, detail="Chatbot not initialized")
        
    logger.info(f"User {current_user['username']} uploading {len(files)} files")
    
    results = []
    for file in files:
        content = await file.read()
        kind = imghdr.what(None, h=content)
        
        if kind not in Allowed_image_type:
            results.append({"filename": file.filename, "error": "Unsupported image type"})
            continue

        if len(content) > 10 * 1024 * 1024:
            results.append({"filename": file.filename, "error": "File too large (max 10MB)"})
            continue

        try:
            text, response = await ocr_and_query(content)
            results.append({
                "filename": file.filename, 
                "extracted_text": text, 
                "response": response
            })
        except Exception as e:
            results.append({"filename": file.filename, "error": str(e)})

    return {"results": results}

@app.post("/reinitialize")
async def reinitialize_chatbot(current_user: dict = Depends(get_current_user)):
    """Reinitialize the chatbot (admin function)"""
    logger.info(f"User {current_user['username']} requested chatbot reinitialization")
    
    success = initialize_chatbot()
    if success:
        return {"message": "Chatbot reinitialized successfully"}
    else:
        raise HTTPException(status_code=500, detail="Failed to reinitialize chatbot")

# Optional: Add a simple test endpoint that doesn't require authentication
@app.post("/test_query")
async def test_query_no_auth(request: SingleQueryRequest):
    """Test query endpoint without authentication (for testing only)"""
    if not chatbot:
        raise HTTPException(status_code=503, detail="Chatbot not initialized")
    
    try:
        result = chatbot.query(request.question, threshold=request.threshold)
        return {"question": request.question, "answer": result, "threshold_used": request.threshold}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

