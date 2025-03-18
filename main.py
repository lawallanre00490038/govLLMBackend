import uvicorn
import os

if __name__ == "__main__":
    ENV = os.getenv("ENV", "development")
    PORT = int(os.getenv("PORT", 10000))  # Render expects port 10000
    HOST = "0.0.0.0"
    uvicorn.run(
        app="app.main:app", 
        host=HOST, 
        port=PORT, 
        reload=True,
    )