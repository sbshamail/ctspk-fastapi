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
    existing_files = []
    errors = []

    # Process each file sequentially to avoid race conditions
    for file in files:
        try:
            # Sanitize the filename - replace spaces with hyphens
            original_filename = file.filename
            sanitized_filename = sanitize_filename(original_filename)
            
            # Check if file already exists in database (with proper case handling)
            existing_media = session.scalar(
                select(UserMedia).where(
                    UserMedia.filename.ilike(sanitized_filename),  # Use ilike for case-insensitive check
                    UserMedia.user_id == user["id"],
                )
            )
            
            if existing_media:
                # File already exists - return existing file info
                existing_files.append(UserMediaRead.model_validate(existing_media))
                continue
            
            # Check if file already exists on disk
            target_folder = os.path.join(MEDIA_DIR, str(user["id"]))
            os.makedirs(target_folder, exist_ok=True)
            file_path = os.path.join(target_folder, sanitized_filename)
            
            if os.path.exists(file_path):
                # File exists on disk but not in DB - add to database
                file_stats = os.stat(file_path)
                size_mb = round(file_stats.st_size / (1024 * 1024), 2)
                
                # Create media record for existing file
                media = UserMedia(
                    user_id=user["id"],
                    filename=sanitized_filename,
                    extension=os.path.splitext(sanitized_filename)[1],
                    original=f"{DOMAIN}/media/{user['email']}/{sanitized_filename}",
                    size_mb=size_mb,
                    thumbnail=None,  # You might want to generate thumbnail if needed
                    media_type="image",
                )
                
                try:
                    session.add(media)
                    session.commit()
                    session.refresh(media)
                    existing_files.append(UserMediaRead.model_validate(media))
                    continue
                except IntegrityError:
                    # Handle race condition - another request might have added the same file
                    session.rollback()
                    existing_media = session.scalar(
                        select(UserMedia).where(
                            UserMedia.filename.ilike(sanitized_filename),
                            UserMedia.user_id == user["id"],
                        )
                    )
                    if existing_media:
                        existing_files.append(UserMediaRead.model_validate(existing_media))
                    continue
            
            # Create a new UploadFile object with sanitized filename for uploadImage function
            content = await file.read()
            
            # Create temporary file for uploadImage processing
            temp_files = []
            try:
                # Create a temporary file with sanitized name
                temp_file_path = os.path.join(target_folder, f"temp_{sanitized_filename}")
                with open(temp_file_path, "wb") as f:
                    f.write(content)
                
                # Create UploadFile object for the uploadImage function
                from fastapi import UploadFile
                from io import BytesIO
                
                temp_upload_file = UploadFile(
                    filename=sanitized_filename,
                    file=BytesIO(content),
                    size=len(content)
                )
                
                # Upload the file using your existing uploadImage function
                saved_files = await uploadImage([temp_upload_file], user, thumbnail)
                
                for file_info in saved_files:
                    # Ensure we're using the sanitized filename
                    file_info["filename"] = sanitize_filename(file_info["filename"])
                    
                    # Insert into database with error handling
                    media = UserMedia(
                        user_id=user["id"],
                        filename=file_info["filename"],
                        extension=file_info["extension"],
                        original=file_info["original"],
                        size_mb=file_info["size_mb"],
                        thumbnail=file_info.get("thumbnail"),
                        media_type="image",
                    )
                    
                    try:
                        session.add(media)
                        session.flush()  # This will raise IntegrityError if duplicate
                        saved_records.append(media)
                    except IntegrityError:
                        session.rollback()
                        # File was added by another process, fetch the existing one
                        existing_media = session.scalar(
                            select(UserMedia).where(
                                UserMedia.filename.ilike(file_info["filename"]),
                                UserMedia.user_id == user["id"],
                            )
                        )
                        if existing_media:
                            existing_files.append(UserMediaRead.model_validate(existing_media))
                        else:
                            # This shouldn't happen, but just in case
                            errors.append(f"Failed to upload {sanitized_filename}: duplicate constraint")
                
            finally:
                # Clean up temporary file
                if os.path.exists(temp_file_path):
                    os.remove(temp_file_path)
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
    response_data = ''
    
    if errors:
        response_data = errors

    # Generate appropriate message
    message_parts = []
    if saved_records:
        message_parts.append(f"Uploaded {len(saved_records)} new files")
        response_data=[UserMediaRead.model_validate(m) for m in saved_records]
    if existing_files:
        message_parts.append(f"{len(existing_files)} files already exist")
        response_data=existing_files
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
    user_dir = os.path.join(MEDIA_DIR, str(user["id"]))
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
                    "original": f"{DOMAIN}/media/{user['email']}/{sanitized_filename}",
                    "thumbnail": f"{DOMAIN}/media/{user['email']}/{name}.webp",
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
        # Sanitize filenames for consistency
        sanitized_filenames = [sanitize_filename(f) for f in filenames]
        stmt = stmt.where(UserMedia.filename.in_([f.lower() for f in sanitized_filenames]))

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
        user_email=str(user["id"]),
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
        user_email=str(user["id"]),
        filenames=filenames,
    )
    if not deleted:
        return api_response(404, "No media found for given filenames")

    return api_response(
        200,
        "Deleted successfully",
        [UserMediaRead.model_validate(m) for m in deleted],
    )