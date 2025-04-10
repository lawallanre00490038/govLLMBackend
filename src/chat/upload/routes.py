# upload_routes.py
from fastapi import APIRouter, UploadFile, Depends, Form
from sqlalchemy.ext.asyncio import AsyncSession
import aiofiles
from src.users.schemas import TokenUser
from src.db.main import get_session
from src.users.auth import get_current_user
from .utils import get_google_token
from .schemas import UploadResponse
from fastapi import UploadFile, File, HTTPException, Query
import os, tempfile
import uuid
from typing import List
import httpx
import mimetypes
import shutil
from .service import FolderIngestion

folder_router = APIRouter()
# ALLOWED_FILE_TYPES = ['image/jpeg', 'image/png', 'application/pdf', 'text/plain']



upload_api = FolderIngestion()



@folder_router.post("/process/folder", response_model=UploadResponse)
async def upload_local_folder(
    files: List[UploadFile] = File(...),
    file_type: str = Query(..., regex="^(pdf|txt|jpg|jpeg|png|mp3|wav)$"),
    user: TokenUser = Depends(get_current_user),
):
    """
    Upload files, validate their types, and process them with the API.
    """

    return await upload_api.upload_files(
        endpoint="uploads",
        files=files,
        file_type=file_type,
        user=user
    )










# # upload_routes.py
# from fastapi import APIRouter, UploadFile, Form, HTTPException
# from fastapi.responses import JSONResponse
# from tempfile import mkdtemp
# import shutil

# @folder_router.post("/google-drive-folder")
# async def handle_google_drive_folder(
#     folder_id: str = Form(..., description="Google Drive Folder ID"),
#     file_type: str = Form(..., regex="^(pdf|image|audio)$"),
#     user: TokenUser = Depends(get_current_user),
#     session: AsyncSession = Depends(get_session)
# ):
#     try:
#         # Create temp directory with cleanup protection
#         temp_dir = mkdtemp(prefix="gd_", dir="/tmp/uploads")
#         folder_uuid = str(uuid.uuid4())
        
#         # Download from Google Drive
#         await download_google_folder(
#             folder_id, 
#             temp_dir,
#             user.access_token  # Stored during OAuth flow
#         )
        
#         # Validate downloaded files
#         valid_files = await validate_file_types(temp_dir, ALLOWED_FILE_TYPES)
#         if not valid_files:
#             raise HTTPException(400, "No valid files found")

#         # Process with external API
#         result = await process_folder_with_api(
#             temp_dir, 
#             file_type,
#             user.access_token
#         )

#         return JSONResponse({
#             "status": "success",
#             "processed_files": len(valid_files),
#             "external_api_response": result
#         })
        
#     except Exception as e:
#         print(f"Google Drive processing failed: {str(e)}")
#         raise HTTPException(500, "Folder processing failed") from e
#     finally:
#         shutil.rmtree(temp_dir, ignore_errors=True)





# # google_drive.py
# from googleapiclient.discovery import build
# from google.oauth2.credentials import Credentials

# async def download_google_folder(folder_id: str, save_path: str, token: str):
#     creds = Credentials(token)
#     service = build('drive', 'v3', credentials=creds)
    
#     try:
#         results = service.files().list(
#             q=f"'{folder_id}' in parents",
#             fields="files(id, name, mimeType)",
#             pageSize=1000
#         ).execute()
        
#         items = results.get('files', [])
#         if not items:
#             raise ValueError("Empty folder")
            
#         for item in items:
#             if item['mimeType'] == 'application/vnd.google-apps.folder':
#                 await download_google_folder(item['id'], 
#                     os.path.join(save_path, item['name']), token)
#             else:
#                 await download_file(service, item['id'], 
#                     os.path.join(save_path, item['name']))
                    
#     except Exception as e:
#         raise RuntimeError(f"Drive API error: {str(e)}") from e

# async def download_file(service, file_id: str, save_path: str):
#     request = service.files().get_media(fileId=file_id)
#     async with aiofiles.open(save_path, 'wb') as fh:
#         downloader = MediaIoBaseUpload(fh, chunksize=1024*1024)
#         await downloader.next_chunk(request)




# async def validate_file_types(temp_dir: str, allowed_types: List[str]) -> bool:
#     """
#     Validate the types of files in the provided directory to match the allowed types.
#     """
#     is_valid = True
    
#     # List files in the temp_dir
#     for filename in os.listdir(temp_dir):
#         file_path = os.path.join(temp_dir, filename)
        
#         if os.path.isfile(file_path):
#             mime_type, _ = mimetypes.guess_type(file_path)
            
#             # Check if the file type is in the allowed list
#             if mime_type not in allowed_types:
#                 is_valid = False
#                 break
    
#     return is_valid


# # external_api.py
# async def process_folder_with_api(folder_path: str, file_type: str, token: str):
#     headers = {
#         "Authorization": f"Bearer {token}",
#         "Content-Type": "application/x-www-form-urlencoded"
#     }
    
#     async with httpx.AsyncClient(timeout=30) as client:
#         response = await client.post(
#             "https://bizllminer.equalyz.ai/process/folder",
#             data={"folder_path": folder_path, "file_type": file_type},
#             headers=headers
#         )
        
#     if response.status_code != 200:
#         print(f"Error: {response.status_code} - {response.text}")
#         raise ChatAPIError()
        
#     return response.json()
