from fastapi import FastAPI
import uvicorn
import os
from starlette.middleware.sessions import SessionMiddleware
from fastapi.middleware.cors import CORSMiddleware
from app.configs.config import SECRET_KEY
from fastapi.openapi.utils import get_openapi
from app.routes.auth.index import router as auth_router

app = FastAPI()
app.include_router(auth_router, prefix="/auth")


# Allow requests from your frontend
origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "https://govllmbackend.onrender.com"
    "*"
]
app.add_middleware(SessionMiddleware, secret_key=SECRET_KEY)
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"], 
    allow_headers=["*"], 
)

@app.get("/")
async def root():
    return {"message": "Welcome to the GovLLMiner API."}


@app.get("/openapi.json", include_in_schema=False)
async def get_openapi_schema():
    """
    Returns the OpenAPI schema in JSON format.
    """
    return get_openapi(
        title="GovLLMiner Authentication API",
        version="1.0.0",
        description="This is the OpenAPI schema for the authentication system.",
        routes=app.routes,
    )


if __name__ == "__main__":
    ENV = os.getenv("ENV", "development")
    PORT = int(os.getenv("PORT", 10000))  # Render expects port 10000
    HOST = "0.0.0.0" if ENV == "production" else "localhost"
    uvicorn.run(
        app="main:app", 
        host="0.0.0.0", 
        port=PORT, 
        reload=True,
    )

# 0.0.0.0