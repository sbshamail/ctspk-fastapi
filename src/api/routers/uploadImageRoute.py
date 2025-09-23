import os
from typing import List

from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import FileResponse

router = APIRouter()

# 📂 Configure this path
MEDIA_DIR = "/var/www/ctspk-media"
os.makedirs(MEDIA_DIR, exist_ok=True)  # ensure folder exists

# ----------------------------
# Upload multiple images (POST)
# ----------------------------
@router.post("/ctspk-media/upload")
async def upload_images(files: List[UploadFile] = File(...)):
    saved_files = []

    for file in files:
        file_path = os.path.join(MEDIA_DIR, file.filename)
        with open(file_path, "wb") as buffer:
            buffer.write(await file.read())
        saved_files.append(file.filename)

    return {"uploaded": saved_files}


# ----------------------------
# Get single image (GET)
# ----------------------------
@router.get("/ctspk-media/{filename}")
async def get_image(filename: str):
    file_path = os.path.join(MEDIA_DIR, filename)
    if not os.path.isfile(file_path):
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(file_path)



# ----------------------------
# Get multiple images (GET)
# ----------------------------
@router.get("/ctspk-media/")
async def get_images(filenames: List[str]):
    """Fetch multiple images by query: /ctspk-media/?filenames=img1.jpg&filenames=img2.jpg"""
    files = []
    for filename in filenames:
        file_path = os.path.join(MEDIA_DIR, filename)
        if os.path.isfile(file_path):
            files.append({"filename": filename, "url": f"/ctspk-media/{filename}"})
        else:
            files.append({"filename": filename, "error": "Not found"})
    return {"files": files}