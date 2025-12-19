import json
import os
import re
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


def sanitize_filename(filename: str) -> str:
    """
    Sanitize filename by:
    - Replacing spaces with hyphens
    - Removing special characters
    - Ensuring safe filename
    """
    # Replace spaces with hyphens
    filename = filename.replace(" ", "-")
    
    # Remove special characters except dots, hyphens, and underscores
    filename = re.sub(r'[^a-zA-Z0-9._-]', '', filename)
    
    # Ensure filename is not empty
    if not filename:
        filename = "uploaded-file"
    
    return filename


@router.post("/create")
async def upload_images(
    session: GetSession,
    user: requireSignin,
    files: List[UploadFile] = File(...),
    thumbnail: bool = False,
):
    saved_records = []
    errors = []

    # Process each file
    for file in files:
        try:
            # Sanitize the filename - replace spaces with hyphens
            original_filename = file.filename
            sanitized_filename = sanitize_filename(original_filename)

            # Read file content
            content = await file.read()

            # Create UploadFile object for the uploadImage function
            from io import BytesIO

            temp_upload_file = UploadFile(
                filename=sanitized_filename,
                file=BytesIO(content),
                size=len(content)
            )

            # Upload the file using uploadImage function (generates unique filename)
            saved_files = await uploadImage([temp_upload_file], user, thumbnail)

            for file_info in saved_files:
                # Insert into database (store path without DOMAIN - serializer adds it)
                media = UserMedia(
                    user_id=user["id"],
                    filename=file_info["filename"],
                    extension=file_info["extension"],
                    original=file_info['original'],
                    size_mb=file_info["size_mb"],
                    thumbnail=file_info.get("thumbnail"),
                    media_type="image",
                )

                session.add(media)
                session.flush()
                saved_records.append(media)

            # Close the UploadFile
            await temp_upload_file.close()

        except Exception as e:
            errors.append(f"Error processing {file.filename}: {str(e)}")
            continue

    # Final commit for all successful operations
    try:
        session.commit()
    except Exception as e:
        session.rollback()
        errors.append(f"Final commit failed: {str(e)}")

    # Prepare response
    response_data = []

    # Generate appropriate message
    message_parts = []
    if saved_records:
        message_parts.append(f"Uploaded {len(saved_records)} new files")
        response_data = [UserMediaRead.model_validate(m) for m in saved_records]
    if errors:
        message_parts.append(f"{len(errors)} errors occurred")

    message = ", ".join(message_parts) if message_parts else "No files processed"

    status_code = 200 if not errors else 207  # 207 Multi-Status if there are errors

    return api_response(status_code, message, response_data)


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
    # Sanitize the filename for consistency
    sanitized_filename = sanitize_filename(filename)
    
    # build the user folder path
    safe_email = str(user["id"])
    user_dir = os.path.join(MEDIA_DIR, safe_email)

    file_path = os.path.join(user_dir, sanitized_filename)

    if not os.path.isfile(file_path):
        return api_response(404, "File not found")
    return FileResponse(file_path)


@router.get("/{email}/{filename}")
async def get_image(email: str, filename: str):
    # Sanitize the filename for consistency
    sanitized_filename = sanitize_filename(filename)
    
    file_path = os.path.join(MEDIA_DIR, email, sanitized_filename)
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
    user_id = str(user["id"])
    user_dir = os.path.join(MEDIA_DIR, user_id)
    results = []

    for filename in data.filenames:
        # Sanitize the filename for consistency
        sanitized_filename = sanitize_filename(filename)

        file_path = os.path.join(user_dir, sanitized_filename)
        if os.path.isfile(file_path):
            name, ext = os.path.splitext(sanitized_filename)
            size_bytes = os.path.getsize(file_path)
            size_kb = round(size_bytes / 1024, 2)
            results.append(
                {
                    "filename": sanitized_filename,
                    "original_filename": filename,  # Keep original name for reference
                    "extension": ext.lower(),
                    "size_kb": size_kb,
                    "original": f"{DOMAIN}/media/{user_id}/{sanitized_filename}",
                    "thumbnail": f"{DOMAIN}/media/{user_id}/{name}_thumb.webp",
                }
            )
        else:
            results.append({
                "filename": filename,
                "sanitized_filename": sanitized_filename,
                "error": "File not found"
            })

    return api_response(200, "Images Found", data=results)


# Delete Multiple

def delete_media_items(
    session: GetSession,
    user_id: int,
    user_folder: str,
    ids: Optional[List[int]] = None,
    filenames: Optional[List[str]] = None,
) -> List[UserMedia]:
    """
    Reusable helper to delete media by IDs or filenames for a specific user.
    Removes files + thumbnails from disk and deletes DB rows.

    Args:
        session: SQLModel session
        user_id: int (owner restriction)
        user_folder: str (user ID as folder name)
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
        # Sanitize filenames for consistency
        sanitized_filenames = [sanitize_filename(f) for f in filenames]
        stmt = stmt.where(UserMedia.filename.in_([f.lower() for f in sanitized_filenames]))

    media_records = session.execute(stmt).scalars().all()
    if not media_records:
        return []

    for media in media_records:
        # --- Delete original file ---
        file_path = os.path.join(MEDIA_DIR, user_folder, media.filename)
        if os.path.exists(file_path):
            os.remove(file_path)

        # --- Delete thumbnail ---
        if media.thumbnail:
            thumb_path = os.path.join(
                MEDIA_DIR, user_folder, os.path.basename(media.thumbnail)
            )
            if os.path.exists(thumb_path):
                os.remove(thumb_path)
        else:
            base, _ = os.path.splitext(media.filename)
            thumb_name = f"{base}_thumb.webp"
            thumb_path = os.path.join(MEDIA_DIR, user_folder, thumb_name)
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
        user_folder=str(user["id"]),
        ids=ids,
    )

    if not deleted:
        return api_response(404, "No matching media found")

    return api_response(
        200,
        "Media deleted successfully",
        [UserMediaRead.model_validate(m) for m in deleted],
    )


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
        user_folder=str(user["id"]),
        filenames=filenames,
    )
    if not deleted:
        return api_response(404, "No media found for given filenames")

    return api_response(
        200,
        "Deleted successfully",
        [UserMediaRead.model_validate(m) for m in deleted],
    )


@router.patch("/fix-double-domain")
async def fix_double_domain(
    session: GetSession,
):
    """
    Fix existing media records that have double DOMAIN in original/thumbnail URLs.
    Removes the DOMAIN prefix so URLs are stored as paths only (e.g., /media/1/file.webp)
    """
    # Get all media records
    stmt = select(UserMedia)
    media_records = session.execute(stmt).scalars().all()

    fixed_count = 0

    for media in media_records:
        updated = False

        # Fix original field - remove DOMAIN prefix if present
        if media.original and media.original.startswith(DOMAIN):
            media.original = media.original.replace(DOMAIN, "", 1)
            updated = True

        # Fix thumbnail field - remove DOMAIN prefix if present
        if media.thumbnail and media.thumbnail.startswith(DOMAIN):
            media.thumbnail = media.thumbnail.replace(DOMAIN, "", 1)
            updated = True

        if updated:
            session.add(media)
            fixed_count += 1

    session.commit()

    return api_response(
        200,
        f"Fixed {fixed_count} media records with double DOMAIN",
        {"fixed_count": fixed_count, "total_records": len(media_records)}
    )