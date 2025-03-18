import uvicorn
import os

if __name__ == "__main__":
    ENV = os.getenv("ENV", "development")
    HOST = "0.0.0.0" if ENV == "production" else "127.0.0.1"
    uvicorn.run(
        app="app.main:app", 
        host=HOST, 
        port=8000, 
        reload=True,
    )