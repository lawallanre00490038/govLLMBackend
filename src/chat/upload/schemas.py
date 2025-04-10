from pydantic import BaseModel
from typing import List, Union, Any
from typing import Optional

class UploadResult(BaseModel):
    filename: Optional[str] = None
    status: str
    message: Optional[str] = None

class UploadResponse(BaseModel):
    status: str
    message: str
    upload_results: List[UploadResult]
