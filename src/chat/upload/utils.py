# file_helpers.py
import shutil
import os

from fastapi import Depends, Request, HTTPException

def unzip_file(zip_path: str, extract_to: str):
    shutil.unpack_archive(zip_path, extract_to)

def delete_folder(path: str):
    if os.path.exists(path):
        shutil.rmtree(path)


async def get_google_token(request: Request):
    token_data = await request.json()
    if not token_data.get("token"):
        raise HTTPException(status_code=400, detail="Google OAuth token missing.")
    return token_data["token"]
