import os
from typing import List

from fastapi import APIRouter, Depends, Path, UploadFile, File, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
from src.api.core.security import require_signin
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
# @router.post("/create")
# async def upload_images(
#     session: GetSession,
#     user: requireSignin,
#     files: List[UploadFile] = File(...),
#     thumbnail: bool = False,
# ):
#     saved_files = await uploadImage(files, user, thumbnail)

#     # create one UserMedia entry with media array
#     media = UserMedia(
#         user_id=user["id"],
#         media=saved_files,
#         media_type="image",  # you can also make this dynamic if needed
#     )
#     session.add(media)
#     session.commit()
#     session.refresh(media)
#     return api_response(
#         200, "Images uploaded successfully", UserMediaRead.model_validate(media)
#     )


@router.post("/create")
async def upload_images(
    session: GetSession,
    user: requireSignin,
    files: List[UploadFile] = File(...),
    thumbnail: bool = False,
):
    saved_files = []

    for file in files:
        # Set your target folder path
        target_folder = f"media/{user['email']}/"
        os.makedirs(target_folder, exist_ok=True)

        file_path = os.path.join(target_folder, file.filename)

        # Check if file already exists
        if os.path.exists(file_path):
            return api_response(400, f"File '{file.filename}' already exists.")

        # Save the file (you can keep your existing uploadImage logic)
        saved_files = await uploadImage(files, user, thumbnail)

    # create one UserMedia entry with media array
    media = UserMedia(
        user_id=user["id"],
        media=saved_files,
        media_type="image",  # optionally dynamic
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
    searchFields = ["id"]

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
                    "original": f"{DOMAIN}/media/{user['email']}/{filename}",
                    "thumbnail": f"{DOMAIN}/media/{user['email']}/{name}.webp",
                }
            )
        else:
            results.append({"filename": filename, "error": "File not found"})

    return api_response(200, "Images Found", data=results)


@router.delete("/delete/{media_id}")
async def delete_media(
    session: GetSession,
    user: requireSignin,
    media_id: int = Path(..., description="ID of the UserMedia entry"),
    filename: str = None,  # optional: delete specific file inside media array
):
    # 1️⃣ Get the media record
    media_record = session.get(UserMedia, media_id)
    if not media_record:
        return api_response(404, "Media record not found")

    # 2️⃣ Ensure this belongs to the user
    if media_record.user_id != user["id"]:
        raise api_response(403, "Unauthorized")

    # 3️⃣ Delete specific file if filename provided
    if filename:
        # filter media list
        new_media_list = []
        deleted = False
        for item in media_record.media:
            if item.get("filename") == filename:
                # delete from filesystem
                file_path = os.path.join(MEDIA_DIR, user["email"], filename)
                if os.path.exists(file_path):
                    os.remove(file_path)
                deleted = True
            else:
                new_media_list.append(item)

        if not deleted:
            raise HTTPException(status_code=404, detail="File not found in media")

        # update media array
        media_record.media = new_media_list

    else:
        # 4️⃣ Delete all files in this media entry
        for item in media_record.media:
            file_path = os.path.join(MEDIA_DIR, user["email"], item.get("filename"))
            if os.path.exists(file_path):
                os.remove(file_path)
        # delete record from DB
        session.delete(media_record)
        session.commit()
        return api_response(200, "Media and all files deleted successfully")

    # commit changes for partial delete
    session.add(media_record)
    session.commit()
    session.refresh(media_record)
    return api_response(
        200, "File deleted successfully", UserMediaRead.model_validate(media_record)
    )


# @router.delete("/delete-multiple")
# async def delete_multiple_images(user: requireSignin, data: FilenameList):
#     user_dir = os.path.join(MEDIA_DIR, user["email"])
#     results = []

#     for filename in data.filenames:
#         file_path = os.path.join(user_dir, filename)
#         if os.path.isfile(file_path):
#             try:
#                 os.remove(file_path)
#                 results.append({"filename": filename, "status": "deleted"})
#             except Exception as e:
#                 api_response(
#                     200,
#                     "Delete Images Successfully",
#                     data={"filename": filename, "status": "error", "detail": str(e)},
#                 )
#         else:
#             api_response(200, "Not Found", data=filename)

#     return api_response(200, "Delete Images Successfully", data=results)
