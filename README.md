Retrieval-Augmented Generation (RAG) Assistant

This project is a modular AI assistant powered by Retrieval-Augmented Generation (RAG).
It combines text and image processing, document embedding & retrieval, and local chat history management into a single system.

🚀 Features

🔎 Retrieval-Augmented Generation (RAG): Uses embeddings stored in MongoDB to enhance responses with relevant context.

📝 Text Processing: Extracts, embeds, and retrieves knowledge from user-provided text.

🖼 Image Processing: Converts images/PDFs into text, embeds the extracted content, and integrates it into RAG workflow.

💾 Local Chat History: Stores past conversations on the user’s device for personalization without requiring a paid vector DB.

⚡ Modular Architecture: Each component (text, image, storage, retrieval) is built as a module for easy extension.

🔐 Cost-Efficient: No external paid services (like Pinecone) — only MongoDB and local storage.

📂 Tech Stack

FastAPI – Backend API framework

MongoDB – Document & embedding storage

SentenceTransformers / OpenAI Embeddings – Embedding generation

LangChain (optional) – RAG orchestration

OCR / Tesseract – Text extraction from images & PDFs

🎯 Use Cases

AI-powered personal assistant

Knowledge retrieval system

Document-based Q&A chatbot

Local RAG setup without cloud costs
