# from fastapi import FastAPI, status
# from fastapi.requests import Request
# from fastapi.responses import JSONResponse
# from fastapi.middleware.cors import CORSMiddleware
# from fastapi.middleware.trustedhost import TrustedHostMiddleware
# from starlette.middleware.sessions import SessionMiddleware
# import time
# from src.config import settings
# import logging

# logger = logging.getLogger("uvicorn.access")
# logger.disabled = True


# def register_middleware(app: FastAPI):

#     @app.middleware("http")
#     async def custom_logging(request: Request, call_next):
#         start_time = time.time()

#         response = await call_next(request)
#         processing_time = time.time() - start_time

#         message = f"{request.client.host}:{request.client.port} - {request.method} - {request.url.path} - {response.status_code} completed after {processing_time}s"

#         print(message)
#         return response
    
#     app.add_middleware(SessionMiddleware, secret_key=settings.SESSION_SECRET_KEY)

#     app.add_middleware(
#         CORSMiddleware,
#         allow_origins=["*"],
#         allow_methods=["*"],
#         allow_headers=["*"],
#         allow_credentials=True,
#     )

#     app.add_middleware(
#     TrustedHostMiddleware,
#     allowed_hosts=[
#         "localhost",
#         "127.0.0.1",
#         "0.0.0.0",
#         "*.onrender.com",
#         "govllmbackend.onrender.com",
#     ],
    
# )





from fastapi import FastAPI, Request, Depends
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from starlette.middleware.sessions import SessionMiddleware
import time
from src.config import settings
import logging
from sqlalchemy.ext.asyncio import AsyncSession
from src.db.main import get_session

logger = logging.getLogger("uvicorn.access")
logger.disabled = True

def register_middleware(app: FastAPI):

    @app.middleware("http")
    async def custom_logging(request: Request, call_next):
        start_time = time.time()
        response = await call_next(request)
        processing_time = time.time() - start_time
        message = f"{request.client.host}:{request.client.port} - {request.method} - {request.url.path} - {response.status_code} completed after {processing_time}s"
        print(message)
        return response
    
    @app.middleware("http")
    async def database_session_middleware(request: Request, call_next):
        try:
            request.state.db = await get_session().__anext__()
            response = await call_next(request)
        finally:
            await request.state.db.close()
        return response

    app.add_middleware(SessionMiddleware, secret_key=settings.SESSION_SECRET_KEY)
    app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"], allow_credentials=True,)
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=["localhost","127.0.0.1","0.0.0.0","*.onrender.com","govllmbackend.onrender.com"],)
