import json
import os
from typing import List

from fastapi import APIRouter, Depends, Path, UploadFile, File, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlmodel import select
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
    print("files===>", files)
    saved_files = []
    print("saved_files===>", saved_files)

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


# helper: delete actual files from disk (safe basename to avoid path traversal)
def _delete_files_for_item(user_email: str, item: dict):
    """Delete file and its thumbnail from disk."""
    fname = item.get("filename") or (
        item.get("original") and os.path.basename(item.get("original"))
    )
    if fname:
        file_path = os.path.join(MEDIA_DIR, user_email, fname)
        if os.path.exists(file_path):
            os.remove(file_path)

        # delete thumbnail if stored
        if item.get("thumbnail"):
            thumb_path = os.path.join(
                MEDIA_DIR, user_email, os.path.basename(item["thumbnail"])
            )
            if os.path.exists(thumb_path):
                os.remove(thumb_path)
        else:
            # fallback thumbnail name
            base, _ = os.path.splitext(fname)
            thumb_name = f"{base}_thumb.webp"
            thumb_path = os.path.join(MEDIA_DIR, user_email, thumb_name)
            if os.path.exists(thumb_path):
                os.remove(thumb_path)


@router.delete("/delete/{id_or_filename}")
async def delete_media(id_or_filename: str, session: GetSession, user: requireSignin):
    # ----- Delete by ID -----
    if id_or_filename.isdigit():
        media_id = int(id_or_filename)
        media_record = session.get(UserMedia, media_id)
        if not media_record:
            return api_response(400, "Media record not found")
        if media_record.user_id != user["id"]:
            return api_response(403, "Unauthorized")

        for item in media_record.media or []:
            _delete_files_for_item(user["email"], item)

        session.delete(media_record)
        session.commit()
        return api_response(200, "Media record and all files deleted")

    # ----- Delete by filename -----
    filename = id_or_filename
    stmt = select(UserMedia).where(UserMedia.user_id == user["id"])
    all_media = session.exec(stmt).all()

    target_record = None

    for rec in all_media:
        print(rec)
        if any(
            m.get("filename", "").strip().lower() == filename.strip().lower()
            for m in (rec.media or [])
        ):
            target_record = rec
            break

    if not target_record:
        return api_response(400, f"File '{filename}' not found for this user")

    # remove file entry
    new_media = [
        m
        for m in (target_record.media or [])
        if m.get("filename", "").strip().lower() != filename.strip().lower()
    ]

    # normalize for schema
    def normalize_media_item(item: dict) -> dict:
        return {
            "filename": item.get("filename"),
            "extension": item.get("extension"),
            "original": item.get("original") or item.get("url"),
            "size_mb": item.get("size_mb"),
            "thumbnail": item.get("thumbnail") or item.get("thumbnail_url"),
        }

    target_record.media = (
        [normalize_media_item(m) for m in new_media] if new_media else None
    )

    if not new_media:
        session.delete(target_record)
    else:
        session.add(target_record)

    session.commit()

    return api_response(
        200,
        f"File '{filename}' deleted successfully",
        UserMediaRead.model_validate(target_record),  # ✅ will now work
    )


# Delete Multiple


class DeleteRequest(BaseModel):
    items: List[str]  # each item can be an id (string digit) or filename


@router.delete("/delete/multiple")
async def delete_multiple(req: DeleteRequest, session: GetSession, user: requireSignin):
    deleted = []
    not_found = []
    print()
    for id_or_filename in req.items:
        # ----- Case 1: Delete by ID -----
        if id_or_filename.isdigit():
            media_id = int(id_or_filename)
            media_record = session.get(UserMedia, media_id)

            if media_record and media_record.user_id == user["id"]:
                # Try to delete files (ignore if not found on disk)
                for item in media_record.media or []:
                    _delete_files_for_item(user["email"], item)

                # Always delete DB record
                session.delete(media_record)
                deleted.append(f"id:{media_id}")
            else:
                not_found.append(f"id:{media_id}")

        # ----- Case 2: Delete by filename -----
        else:
            filename = id_or_filename
            removed_from_db = False
            removed_from_disk = False

            # Delete from disk if exists
            file_path = os.path.join(MEDIA_DIR, user["email"], filename)
            if os.path.exists(file_path):
                os.remove(file_path)
                # thumbnail too
                base, _ = os.path.splitext(filename)
                thumb_path = os.path.join(
                    MEDIA_DIR, user["email"], f"{base}_thumb.webp"
                )
                if os.path.exists(thumb_path):
                    os.remove(thumb_path)
                removed_from_disk = True

            # Delete from DB if exists
            stmt = select(UserMedia).where(UserMedia.user_id == user["id"])
            all_media = session.exec(stmt).all()

            for rec in all_media:
                if any(m.get("filename") == filename for m in (rec.media or [])):
                    new_media = [m for m in rec.media if m.get("filename") != filename]
                    rec.media = new_media
                    if not new_media:
                        session.delete(rec)
                    else:
                        session.add(rec)
                    removed_from_db = True
                    break

            if removed_from_db or removed_from_disk:
                deleted.append(filename)
            else:
                not_found.append(filename)

    session.commit()

    detail = f"Deleted: {deleted}" if deleted else "No deletions"
    if not_found:
        detail += f" | Not found: {not_found}"

    return api_response(200, detail, {"deleted": deleted, "not_found": not_found})


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
