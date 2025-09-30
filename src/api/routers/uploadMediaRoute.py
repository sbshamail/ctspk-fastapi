import json
import os
from sqlalchemy.exc import IntegrityError

from typing import List, Optional

from fastapi import APIRouter, Depends, Path, Query, UploadFile, File, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlmodel import select
from src.api.core.security import require_signin
from src.api.core.operation import listRecords
from src.api.models.userMediaModel import MediaItem, UserMedia, UserMediaRead
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


@router.post("/create")
async def upload_images(
    session: GetSession,
    user: requireSignin,
    files: List[UploadFile] = File(...),
    thumbnail: bool = False,
):
    saved_records = []

    # 🔑 Save files to disk + build file_info dicts
    saved_files = await uploadImage(files, user, thumbnail)

    for file_info in saved_files:
        existing_media = session.scalar(
            select(UserMedia).where(
                UserMedia.filename == file_info["filename"],
                UserMedia.user_id == user["id"],  # if filename uniqueness is per user
            )
        )
        if existing_media:
            return api_response(
                400, f"File '{file_info['filename']}' already exists in database."
            )
        target_folder = f"media/{user['email']}/"
        os.makedirs(target_folder, exist_ok=True)

        file_path = os.path.join(target_folder, file_info["filename"])

        # ✅ Duplicate check
        if os.path.exists(file_path):
            return api_response(400, f"File '{file_info['filename']}' already exists.")

        # ✅ Insert each file as its own row
        media = UserMedia(
            user_id=user["id"],
            filename=file_info["filename"],
            extension=file_info["extension"],
            original=file_info["original"],
            size_mb=file_info["size_mb"],
            thumbnail=file_info.get("thumbnail"),
            media_type="image",
        )
        session.add(media)
        session.flush()  # get `id` immediately
        saved_records.append(media)

    session.commit()
    return api_response(
        200,
        "Images uploaded successfully",
        [UserMediaRead.model_validate(m) for m in saved_records],
    )


# ✅ READ (single)
@router.get("/read/{id}", response_model=UserMediaRead)
def get(id: int, session: GetSession):
    read = session.get(UserMedia, id)
    raiseExceptions((read, 404, "Media not found"))

    return api_response(200, "Media Found", UserMediaRead.model_validate(read))


@router.get("/list/user", response_model=list[UserMediaRead])
def list(query_params: ListQueryParams, user: requireSignin):
    query_params = vars(query_params)
    searchFields = ["id", "media_type"]

    return listRecords(
        query_params=query_params,
        searchFields=searchFields,
        customFilters=[["user_id", user["id"]]],
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


# Delete Multiple


def delete_media_items(
    session: GetSession,
    user_id: int,
    user_email: str,
    ids: Optional[List[int]] = None,
    filenames: Optional[List[str]] = None,
) -> List[UserMedia]:
    """
    Reusable helper to delete media by IDs or filenames for a specific user.
    Removes files + thumbnails from disk and deletes DB rows.

    Args:
        session: SQLModel session
        user_email: str (used to build disk path)
        user_id: int (owner restriction)
        ids: list of media IDs to delete
        filenames: list of filenames to delete (case-insensitive)

    Returns:
        List of deleted UserMedia rows
    """

    if not ids and not filenames:
        raise ValueError("Must provide either ids or filenames to delete.")

    stmt = select(UserMedia).where(UserMedia.user_id == user_id)

    if ids:
        stmt = stmt.where(UserMedia.id.in_(ids))
    if filenames:
        stmt = stmt.where(UserMedia.filename.in_([f.lower() for f in filenames]))

    media_records = session.exec(stmt).all()
    if not media_records:
        return []

    for media in media_records:
        # --- Delete original file ---
        file_path = os.path.join(MEDIA_DIR, user_email, media.filename)
        if os.path.exists(file_path):
            os.remove(file_path)

        # --- Delete thumbnail ---
        if media.thumbnail:
            thumb_path = os.path.join(
                MEDIA_DIR, user_email, os.path.basename(media.thumbnail)
            )
            if os.path.exists(thumb_path):
                os.remove(thumb_path)
        else:
            base, _ = os.path.splitext(media.filename)
            thumb_name = f"{base}_thumb.webp"
            thumb_path = os.path.join(MEDIA_DIR, user_email, thumb_name)
            if os.path.exists(thumb_path):
                os.remove(thumb_path)

        # --- Remove from DB ---
        session.delete(media)

    session.commit()
    return media_records


@router.delete("/delete-by-ids")
async def delete_by_ids(
    session: GetSession,
    user: requireSignin,
    ids: List[int] = Query(
        ..., description="IDs of media to delete"
    ),  # e.g. /media/delete-by-ids?ids=1&ids=2&ids=3
):
    deleted = delete_media_items(
        session=session,
        user_id=user["id"],
        user_email=user["email"],
        ids=ids,
    )

    if not deleted:
        return api_response(404, "No matching media found")

    return api_response(
        200,
        "Media deleted successfully",
        [UserMediaRead.model_validate(m) for m in deleted],
    )


from fastapi import Query
from typing import List


@router.delete("/delete-by-filenames")
async def delete_by_filenames(
    session: GetSession,
    user: requireSignin,
    filenames: List[str] = Query(
        ...,
        description="Filenames of media to delete. Example: ?filenames=1.webp&filenames=2.webp",
    ),
):
    deleted = delete_media_items(
        session=session,
        user_id=user["id"],
        user_email=user["email"],
        filenames=filenames,
    )
    if not deleted:
        return api_response(404, "No media found for given filenames")

    return api_response(
        200,
        "Deleted successfully",
        [UserMediaRead.model_validate(m) for m in deleted],
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
