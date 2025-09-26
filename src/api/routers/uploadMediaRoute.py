import os
from typing import List

from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
from src.api.core.operation import listRecords
from src.api.models.userMediaModel import UserMedia, UserMediaRead
from src.api.core.operation.media import uploadImage
from src.api.core.dependencies import GetSession, ListQueryParams
from src.api.core.response import api_response, raiseExceptions
from src.config import DOMAIN

from src.api.core import (
    requireSignin,
)


router = APIRouter(prefix="/media", tags=["Media"])


# 📂 Configure this path
MEDIA_DIR = "/var/www/ctspk-media"
os.makedirs(MEDIA_DIR, exist_ok=True)  # ensure folder exists


# ----------------------------
# Upload multiple images (POST)
# ----------------------------
@router.post("/create")
async def upload_images(
    user: requireSignin,
    session: GetSession,
    files: List[UploadFile] = File(...),
    thumbnail: bool = False,
):
    saved_files = await uploadImage(files, user, thumbnail)

    # create one UserMedia entry with media array
    media = UserMedia(
        user_id=user["id"],
        media=saved_files,
        media_type="image",  # you can also make this dynamic if needed
    )
    session.add(media)
    session.commit()
    session.refresh(media)
    return api_response(
        200, "Images uploaded successfully", UserMediaRead.model_validate(media)
    )


# ✅ READ (single)
@router.get("/read/{id}", response_model=UserMediaRead)
def get(id: int, session: GetSession):
    read = session.get(UserMedia, id)
    raiseExceptions((read, 404, "Media not found"))

    return api_response(200, "Media Found", UserMediaRead.model_validate(read))


@router.get("/list", response_model=list[UserMediaRead])
def list(query_params: ListQueryParams):
    query_params = vars(query_params)
    searchFields = ["media_type"]

    return listRecords(
        query_params=query_params,
        searchFields=searchFields,
        Model=UserMedia,
        Schema=UserMediaRead,
    )


# ----------------------------
# Get single image (GET)
# ----------------------------
@router.get("/{filename}")
async def get_image(user: requireSignin, filename: str):
    # build the user folder path
    safe_email = user["email"]
    user_dir = os.path.join(MEDIA_DIR, safe_email)

    file_path = os.path.join(user_dir, filename)

    if not os.path.isfile(file_path):
        return api_response(404, "File not found")
    return FileResponse(file_path)


@router.get("/{email}/{filename}")
async def get_image(email: str, filename: str):
    file_path = os.path.join(MEDIA_DIR, email, filename)
    if not os.path.isfile(file_path):
        api_response(404, "File not found")
    return FileResponse(file_path)


# ----------------------------
# Get multiple images (GET)
# ----------------------------


class FilenameList(BaseModel):
    filenames: List[str]


@router.post("/get-multiple")
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
                    "thumbnail_url": f"{DOMAIN}/media/{user['email']}/{name}.webp",
                }
            )
        else:
            results.append({"filename": filename, "error": "File not found"})

    return api_response(200, "Images Found", data=results)


@router.delete("/delete-multiple")
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
                api_response(
                    200,
                    "Delete Images Successfully",
                    data={"filename": filename, "status": "error", "detail": str(e)},
                )
        else:
            api_response(200, "Not Found", data=filename)

    return api_response(200, "Delete Images Successfully", data=results)
