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
