@"
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from app.models.user import User
from app.core.security import get_current_active_user
from app.core.azure_storage import upload_photo, upload_avatar

router = APIRouter()

@router.post("/photo")
async def upload_eco_photo(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_active_user)
):
    """エコ活動写真をアップロード"""
    try:
        result = await upload_photo(file)
        return {
            "success": True,
            "filename": result["filename"],
            "url": result["url"],
            "message": "写真がアップロードされました"
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/avatar")
async def upload_user_avatar(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_active_user)
):
    """ユーザーアバターをアップロード"""
    try:
        result = await upload_avatar(file)
        return {
            "success": True,
            "filename": result["filename"],
            "url": result["url"],
            "message": "アバターがアップロードされました"
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
"@ | Out-File -FilePath app\api\uploads.py -Encoding UTF8