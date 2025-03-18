import uvicorn

import os

if __name__ == "__main__":
    ENV = os.getenv("ENV", "development")
    HOST = "0.0.0.0" if ENV == "production" else "127.0.0.1"
    PORT = int(os.getenv("PORT", 8000)) 
    uvicorn.run(
        "app.main:app", 
        host=HOST, 
        port=PORT, 
        reload=(ENV == "development")
    )