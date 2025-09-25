import os
from typing import List

from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
from src.config import DOMAIN
from src.api.core import (
    requireSignin,
)
from PIL import Image

router = APIRouter()

# 📂 Configure this path
MEDIA_DIR = "/var/www/ctspk-media"
os.makedirs(MEDIA_DIR, exist_ok=True)  # ensure folder exists

MAX_SIZE = 1 * 1024 * 1024  # 1 MB


# ----------------------------
# Upload multiple images (POST)
# ----------------------------
@router.post("/media/upload")
async def upload_images(user: requireSignin, files: List[UploadFile] = File(...)):
    saved_files = []

    # create a folder for this user (use email or id)
    user_dir = os.path.join(MEDIA_DIR, user["email"])
    os.makedirs(user_dir, exist_ok=True)

    for file in files:
        # Get extension (lowercase)
        ext = os.path.splitext(file.filename)[1].lower()

        # If file is already webp/avif, save directly
        if ext in [".webp", ".avif"]:
            file_path = os.path.join(user_dir, file.filename)
            with open(file_path, "wb") as buffer:
                buffer.write(await file.read())
        else:
            # Convert to WebP
            img = Image.open(file.file).convert("RGB")
            output_filename = os.path.splitext(file.filename)[0] + ".webp"
            file_path = os.path.join(user_dir, output_filename)
            img.save(file_path, "webp", quality=80, method=6)

        # Check file size
        size_bytes = os.path.getsize(file_path)
        if size_bytes > MAX_SIZE:
            os.remove(file_path)  # cleanup
            size_mb = round(size_bytes / (1024 * 1024), 2)
            raise HTTPException(
                status_code=400,
                detail=f"{file.filename} is still larger than 1 MB after optimization "
                f"({size_mb} MB)",
            )

        saved_files.append(
            {
                "filename": os.path.basename(file_path),
                "extension": ext,
                "url": f"{DOMAIN}/media/{user['email']}/{os.path.basename(file_path)}",
            }
        )

    return {"uploaded": saved_files}


# ----------------------------
# Get single image (GET)
# ----------------------------
@router.get("/media/{filename}")
async def get_image(user: requireSignin, filename: str):
    # build the user folder path
    safe_email = user["email"]
    print(safe_email)
    user_dir = os.path.join(MEDIA_DIR, safe_email)

    file_path = os.path.join(user_dir, filename)

    if not os.path.isfile(file_path):
        raise HTTPException(status_code=404, detail="File not found")

    return FileResponse(file_path)


@router.get("/media/{email}/{filename}")
async def get_image(email: str, filename: str):
    file_path = os.path.join(MEDIA_DIR, email, filename)
    if not os.path.isfile(file_path):
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(file_path)


# ----------------------------
# Get multiple images (GET)
# ----------------------------


class FilenameList(BaseModel):
    filenames: List[str]


@router.post("/media/get-multiple")
async def get_multiple_images(user: requireSignin, data: FilenameList):
    user_dir = os.path.join(MEDIA_DIR, user["email"])
    results = []

    for filename in data.filenames:
        file_path = os.path.join(user_dir, filename)
        if os.path.isfile(file_path):
            name, ext = os.path.splitext(filename)
            size_bytes = os.path.getsize(file_path)
            size_kb = round(size_bytes / 1024, 2)
            results.append(
                {
                    "filename": filename,
                    "extension": ext.lower(),
                    "size_kb": size_kb,
                    "url": f"{DOMAIN}/media/{user['email']}/{filename}",
                }
            )
        else:
            results.append({"filename": filename, "error": "File not found"})

    return {"results": results}


@router.delete("/media/delete-multiple")
async def delete_multiple_images(user: requireSignin, data: FilenameList):
    user_dir = os.path.join(MEDIA_DIR, user["email"])
    results = []

    for filename in data.filenames:
        file_path = os.path.join(user_dir, filename)
        if os.path.isfile(file_path):
            try:
                os.remove(file_path)
                results.append({"filename": filename, "status": "deleted"})
            except Exception as e:
                results.append(
                    {"filename": filename, "status": "error", "detail": str(e)}
                )
        else:
            results.append({"filename": filename, "status": "not found"})

    return {"results": results}
