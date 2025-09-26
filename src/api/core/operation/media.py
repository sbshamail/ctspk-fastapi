import os
from src.api.core.response import api_response
from PIL import Image, UnidentifiedImageError


ALLOWED_RAW_EXT = [".webp", ".avif", ".ico", ".svg"]
MEDIA_DIR = "/var/www/ctspk-media"
os.makedirs(MEDIA_DIR, exist_ok=True)  # ensure folder exists
MAX_SIZE = 1 * 1024 * 1024  # 1 MB
THUMBNAIL_SIZE = (300, 300)  # max width/height


async def uploadImage(files, user, thumbnail):
    saved_files = []

    user_dir = os.path.join(MEDIA_DIR, user["email"])
    os.makedirs(user_dir, exist_ok=True)

    for file in files:
        ext = os.path.splitext(file.filename)[1].lower()
        file_path = os.path.join(user_dir, file.filename)

        if ext in ALLOWED_RAW_EXT:
            # save directly
            with open(file_path, "wb") as buffer:
                buffer.write(await file.read())
        else:
            try:
                # Convert to WebP
                img = Image.open(file.file).convert("RGB")
                output_filename = os.path.splitext(file.filename)[0] + ".webp"
                file_path = os.path.join(user_dir, output_filename)
                img.save(file_path, "webp", quality=80, method=6)
                ext = ".webp"  # update extension
            except UnidentifiedImageError:
                raise api_response(
                    400,
                    f"File type {ext} is not a supported image format.",
                )

        # check size
        size_bytes = os.path.getsize(file_path)
        if size_bytes > MAX_SIZE:
            os.remove(file_path)
            size_mb = round(size_bytes / (1024 * 1024), 2)
            return api_response(
                400,
                f"{file.filename} is still larger than 1 MB after optimization ({size_mb} MB)",
            )
        file_info = {
            "filename": os.path.basename(file_path),
            "extension": ext,
            "url": f"/media/{user['email']}/{os.path.basename(file_path)}",
            "size_mb": round(size_bytes / (1024 * 1024), 2),
        }
        # ✅ Generate thumbnail if requested and format supported
        if thumbnail and ext in [".jpg", ".jpeg", ".png", ".webp"]:
            thumb_name = (
                os.path.splitext(os.path.basename(file_path))[0] + "_thumb.webp"
            )
            thumb_path = os.path.join(user_dir, thumb_name)

            with Image.open(file_path) as img:
                img.thumbnail(THUMBNAIL_SIZE)
                img.save(thumb_path, "webp", quality=80, method=6)

            file_info["thumbnail_url"] = f"/media/{user['email']}/{thumb_name}"

        saved_files.append(file_info)
        return saved_files
