import os
import zipfile
import shutil
from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse

router = APIRouter()

# Location to store uploaded and extracted codebases
UPLOAD_DIR = "./repositories"

@router.post("/upload")
async def upload_codebase_zip(file: UploadFile = File(...)):
    """Upload a zipped repository, extract it locally, and return the local path."""
    if not file.filename.endswith(".zip"):
        raise HTTPException(status_code=400, detail="Only ZIP files are supported.")
        
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    zip_path = os.path.join(UPLOAD_DIR, file.filename)
    
    # Save the uploaded ZIP file
    try:
        with open(zip_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save upload: {e}")
        
    # Extract directory name
    folder_name = file.filename[:-4]
    extract_path = os.path.join(UPLOAD_DIR, folder_name)
    
    # Extract the ZIP contents
    try:
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(extract_path)
        # Remove the ZIP archive file after extraction
        os.remove(zip_path)
    except Exception as e:
        if os.path.exists(extract_path):
            shutil.rmtree(extract_path)
        raise HTTPException(status_code=500, detail=f"Extraction failed: {e}")
        
    return JSONResponse(
        status_code=200,
        content={
            "success": True,
            "message": "ZIP file uploaded and extracted successfully.",
            "repo_path": os.path.abspath(extract_path)
        }
    )
