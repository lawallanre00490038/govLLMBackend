from fastapi import FastAPI
from src.users.routes import auth_router
from src.middleware import register_middleware
from src.errors import register_all_errors
import uvicorn, os
from src.db.main import create_tables
from contextlib import asynccontextmanager
import logging
from src.chat.routes import chat_router

# # logging.basicConfig(level=logging.DEBUG)
# logging.basicConfig()    
# logging.getLogger("sqlalchemy.engine").setLevel(logging.DEBUG)

version = "v1"

description = """
A REST API for the AI GovLLMiner Platform.

The GovLLmer project is focused on developing a comprehensive chat interface with user registration and authentication. The system will allow users to initiate new chats, view chat history in a panel interface, and interact with stored chat histories, including images and files. The chat interface will support drag-and-drop file uploads, with a separate UI for batch file uploads used in Retrieval-Augmented Generation (RAG) and fine-tuning purposes. Additionally, the app will process different types of files, such as handwritten images through OCR integration and audio files through Speech-to-Text (STT) integration.

The system will include predefined query templates and employ machine learning models, such as pre-trained transformers, for query pre-processing and categorization. The RAG pipeline will index various file types and store them in a vector database. The app will allow for query prompt engineering, utilizing open-source LLM APIs to process and fine-tune data. These fine-tuned models will be deployed as APIs for backend integration.

To enhance performance, the app will incorporate caching mechanisms to optimize query results, as well as a feedback system where users can flag incorrect responses and suggest corrections. Lastly, the platform will automatically scale its resources depending on demand, ensuring optimal performance during peak usage.
"""

version_prefix = f"/api/{version}"


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Application starting...")
    await create_tables()
    yield
    print("Application shutting down...")


app = FastAPI(
    lifespan=lifespan,
    title="GovLLMiner",
    description=description,
    version=version,
    license_info={"name": "MIT License", "url": "https://opensource.org/license/mit"},
    contact={
        "name": "EqualyzAI",
        "url": "https://equalyz.ai/",
        "email": "uche@equalyz.ai",
    },
    terms_of_service="https://equalyz.ai/about-us/",
    openapi_url=f"{version_prefix}/openapi.json",
    docs_url=f"{version_prefix}/docs",
    redoc_url=f"{version_prefix}/redoc"
)


@app.get("/")
async def root():
    return {"message": "Welcome to GovLLminer API"}

# Register error handlers and middleware
register_all_errors(app)
register_middleware(app)

# Include authentication router
app.include_router(
    auth_router, 
    prefix=f"{version_prefix}/auth", 
    tags=["Auth"]
)

app.include_router(
    chat_router,
    prefix=f"{version_prefix}/chat",
    tags=["Chat"]
)

if __name__ == "__main__":
    ENV = os.getenv("ENV", "development")
    PORT = int(os.getenv("PORT", 10000))
    HOST = "0.0.0.0" if ENV == "production" else "localhost"
    
    uvicorn.run(
        app="main:app",
        host="0.0.0.0",
        port=PORT,
        reload=True if ENV == "development" else False,
        proxy_headers=True
    )
