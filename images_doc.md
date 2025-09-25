# Images Upload Code Versions

## POST Upload Functions

```python
# simple upload many
@router.post("/media/upload")
async def upload_images(user: requireSignin, files: List[UploadFile] = File(...)):
    saved_files = []

    for file in files:
        file_path = os.path.join(MEDIA_DIR, file.filename)
        with open(file_path, "wb") as buffer:
            buffer.write(await file.read())
        saved_files.append(file.filename)

    return {"uploaded": saved_files}
    #---------------------------------------------
# upload on user folder
@router.post("/media/upload")
async def upload_images(user: requireSignin, files: List[UploadFile] = File(...)):
    saved_files = []

    # create a folder for this user (use email or id)
    user_dir = os.path.join(MEDIA_DIR, user["email"])
    os.makedirs(user_dir, exist_ok=True)

    for file in files:
        file_path = os.path.join(user_dir, file.filename)
        with open(file_path, "wb") as buffer:
            buffer.write(await file.read())
        saved_files.append(f"{user['email']}/{file.filename}")

    return {"uploaded": saved_files}
    #-------------------------------------------------
# multiple image
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
```

## GET Functions

```python
# Simple Get
@router.get("/media/{filename}")
async def get_image(filename: str):
    file_path = os.path.join(MEDIA_DIR, filename)
    if not os.path.isfile(file_path):
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(file_path)
# Get From user Folder
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
# access email get image
@router.get("/media/{email}/{filename}")
async def get_image(email: str, filename: str):
    file_path = os.path.join(MEDIA_DIR, email, filename)
    if not os.path.isfile(file_path):
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(file_path)


```
