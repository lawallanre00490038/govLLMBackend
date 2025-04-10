# folder_ingestion.py
from .utils import delete_folder
from src.db.models import FolderUpload
from src.errors import FolderIngestionError, FileUploadError
from sqlalchemy.ext.asyncio import AsyncSession
import httpx
from fastapi import HTTPException
from .schemas import UploadResponse
from src.users.schemas import TokenUser
import os
import tempfile
import uuid
import shutil
from typing import List



class FolderIngestion:
    def __init__(self):
        self.base_url = "https://bizllminer.equalyz.ai"
        self.client = httpx.AsyncClient()

    async def upload_file_to_api(self, endpoint, file_content: bytes, file_path: str, token: str):
        headers = {"Authorization": f"Bearer {token}"}
        url = f"{self.base_url}/{endpoint}"

        try:
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.post(
                    url,
                    files={"file": (os.path.basename(file_path), file_content)},
                    headers=headers
                )
            if response.status_code != 200:
                print(f"Upload failed: {response.status_code} - {response.text}")
                raise FileUploadError()

            return response.json()  
        except httpx.HTTPStatusError as e:
            print(f"HTTP error: {e}")
            raise FileUploadError()
    

    async def upload_files(self, endpoint, files: list, file_type: str, user: TokenUser) -> UploadResponse:
        base_tmp = tempfile.gettempdir()
        temp_dir = os.path.join(base_tmp, "uploads", str(uuid.uuid4()))
        os.makedirs(temp_dir, exist_ok=True)

        valid_files = []
        try:
            invalid_files = [
                file.filename for file in files
                if not file.filename.lower().endswith(f".{file_type}")
            ]
            if invalid_files:
                raise FileUploadError()

            # Save files
            for file in files:
                file_path = os.path.join(temp_dir, file.filename)
                with open(file_path, "wb") as f:
                    f.write(await file.read())
                valid_files.append(file_path)

            # Upload to external API
            upload_results = []
            for file_path in valid_files:
                with open(file_path, "rb") as f:
                    file_content = f.read()
                    upload_result = await self.upload_file_to_api(endpoint, file_content, file_path, user.access_token)
                    upload_results.append(upload_result)

            return UploadResponse(
                status="success",
                message="Files uploaded and processed",
                upload_results=upload_results,
            )
        
        except HTTPException as e:
            raise FileUploadError()
        
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)
