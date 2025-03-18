import uvicorn
import os

if __name__ == "__main__":
    ENV = os.getenv("ENV", "development")  # Default to 'development'
    HOST = "0.0.0.0" if ENV == "production" else "127.0.0.1"  # Use 127.0.0.1 for local dev

    print(f"Running in {ENV} environment")

    uvicorn.run(
        "app.main:app", 
        host=HOST, 
        port=8000, 
        reload=(ENV == "development"), 
    )
