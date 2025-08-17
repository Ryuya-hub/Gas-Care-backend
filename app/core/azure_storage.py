@"
import os
import uuid
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from azure.storage.blob import BlobServiceClient, BlobClient, ContainerClient
from azure.storage.blob import generate_blob_sas, BlobSasPermissions
from azure.core.exceptions import AzureError, ResourceNotFoundError
from fastapi import UploadFile, HTTPException
import aiofiles
import asyncio
from PIL import Image
import io

from app.config import settings

logger = logging.getLogger(__name__)

class AzureStorageService:
    """Azure Blob Storage サービス"""
    
    def __init__(self):
        self.connection_string = settings.AZURE_STORAGE_CONNECTION_STRING
        self.container_name = settings.AZURE_STORAGE_CONTAINER_NAME
        self.account_name = settings.AZURE_STORAGE_ACCOUNT_NAME
        self.account_key = settings.AZURE_STORAGE_ACCOUNT_KEY
        
        if self.connection_string:
            try:
                self.blob_service_client = BlobServiceClient.from_connection_string(
                    self.connection_string
                )
                self._ensure_container_exists()
            except Exception as e:
                logger.error(f"Failed to initialize Azure Storage: {e}")
                self.blob_service_client = None
        else:
            logger.warning("Azure Storage not configured")
            self.blob_service_client = None
    
    def _ensure_container_exists(self):
        """コンテナの存在確認・作成"""
        try:
            container_client = self.blob_service_client.get_container_client(
                self.container_name
            )
            if not container_client.exists():
                container_client.create_container(public_access="blob")
                logger.info(f"Created container: {self.container_name}")
        except Exception as e:
            logger.error(f"Failed to ensure container exists: {e}")
    
    def _generate_unique_filename(self, original_filename: str) -> str:
        """ユニークなファイル名を生成"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        unique_id = str(uuid.uuid4())[:8]
        name, ext = os.path.splitext(original_filename)
        return f"{timestamp}_{unique_id}_{name}{ext}"
    
    def _validate_file_type(self, content_type: str) -> bool:
        """ファイルタイプの検証"""
        return content_type.lower() in settings.ALLOWED_FILE_TYPES
    
    def _validate_file_size(self, file_size: int) -> bool:
        """ファイルサイズの検証"""
        return file_size <= settings.MAX_FILE_SIZE
    
    async def upload_file(
        self, 
        file: UploadFile, 
        folder: str = "uploads",
        resize_image: bool = True,
        max_width: int = 1200,
        max_height: int = 1200
    ) -> Dict[str, Any]:
        """ファイルをアップロード"""
        if not self.blob_service_client:
            raise HTTPException(
                status_code=503,
                detail="ストレージサービスが利用できません"
            )
        
        # ファイル検証
        if not self._validate_file_type(file.content_type):
            raise HTTPException(
                status_code=400,
                detail=f"サポートされていないファイル形式です: {file.content_type}"
            )
        
        # ファイル内容を読み取り
        file_content = await file.read()
        file_size = len(file_content)
        
        if not self._validate_file_size(file_size):
            raise HTTPException(
                status_code=400,
                detail=f"ファイルサイズが大きすぎます。最大: {settings.MAX_FILE_SIZE / (1024*1024):.1f}MB"
            )
        
        try:
            # 画像の場合はリサイズ処理
            if resize_image and file.content_type.startswith('image/'):
                file_content = await self._resize_image(
                    file_content, max_width, max_height
                )
            
            # ユニークなファイル名を生成
            unique_filename = self._generate_unique_filename(file.filename)
            blob_name = f"{folder}/{unique_filename}"
            
            # Blobクライアントを取得
            blob_client = self.blob_service_client.get_blob_client(
                container=self.container_name,
                blob=blob_name
            )
            
            # ファイルをアップロード
            blob_client.upload_blob(
                file_content,
                content_type=file.content_type,
                overwrite=True,
                metadata={
                    "original_filename": file.filename,
                    "upload_timestamp": datetime.utcnow().isoformat(),
                    "file_size": str(len(file_content))
                }
            )
            
            # パブリックURLを生成
            blob_url = blob_client.url
            
            return {
                "filename": unique_filename,
                "original_filename": file.filename,
                "blob_name": blob_name,
                "url": blob_url,
                "content_type": file.content_type,
                "size": len(file_content),
                "upload_timestamp": datetime.utcnow()
            }
            
        except AzureError as e:
            logger.error(f"Azure upload error: {e}")
            raise HTTPException(
                status_code=500,
                detail="ファイルのアップロードに失敗しました"
            )
        except Exception as e:
            logger.error(f"Upload error: {e}")
            raise HTTPException(
                status_code=500,
                detail="ファイルの処理中にエラーが発生しました"
            )
    
    async def _resize_image(
        self, 
        image_content: bytes, 
        max_width: int, 
        max_height: int
    ) -> bytes:
        """画像をリサイズ"""
        try:
            image = Image.open(io.BytesIO(image_content))
            
            # EXIFデータに基づいて回転
            if hasattr(image, '_getexif'):
                exif = image._getexif()
                if exif is not None:
                    orientation = exif.get(274)  # Orientation tag
                    if orientation == 3:
                        image = image.rotate(180, expand=True)
                    elif orientation == 6:
                        image = image.rotate(270, expand=True)
                    elif orientation == 8:
                        image = image.rotate(90, expand=True)
            
            # リサイズ
            image.thumbnail((max_width, max_height), Image.Resampling.LANCZOS)
            
            # RGBモードに変換（JPEG保存用）
            if image.mode in ('RGBA', 'LA', 'P'):
                background = Image.new('RGB', image.size, (255, 255, 255))
                if image.mode == 'P':
                    image = image.convert('RGBA')
                background.paste(image, mask=image.split()[-1] if 'A' in image.mode else None)
                image = background
            
            # バイト配列に保存
            output = io.BytesIO()
            image.save(output, format='JPEG', quality=85, optimize=True)
            return output.getvalue()
            
        except Exception as e:
            logger.error(f"Image resize error: {e}")
            return image_content  # リサイズに失敗した場合は元のファイルを返す
    
    async def delete_file(self, filename: str, folder: str = "uploads") -> bool:
        """ファイルを削除"""
        if not self.blob_service_client:
            return False
        
        try:
            blob_name = f"{folder}/{filename}"
            blob_client = self.blob_service_client.get_blob_client(
                container=self.container_name,
                blob=blob_name
            )
            blob_client.delete_blob()
            return True
            
        except ResourceNotFoundError:
            logger.warning(f"File not found for deletion: {filename}")
            return False
        except AzureError as e:
            logger.error(f"Azure delete error: {e}")
            return False
    
    def generate_sas_url(
        self, 
        filename: str, 
        folder: str = "uploads",
        expires_in_hours: int = 1
    ) -> Optional[str]:
        """SAS URLを生成（一時的なアクセス用）"""
        if not self.blob_service_client or not self.account_key:
            return None
        
        try:
            blob_name = f"{folder}/{filename}"
            
            # SAS トークンを生成
            sas_token = generate_blob_sas(
                account_name=self.account_name,
                account_key=self.account_key,
                container_name=self.container_name,
                blob_name=blob_name,
                permission=BlobSasPermissions(read=True),
                expiry=datetime.utcnow() + timedelta(hours=expires_in_hours)
            )
            
            # SAS URLを構築
            blob_client = self.blob_service_client.get_blob_client(
                container=self.container_name,
                blob=blob_name
            )
            
            return f"{blob_client.url}?{sas_token}"
            
        except Exception as e:
            logger.error(f"SAS URL generation error: {e}")
            return None
    
    def list_files(
        self, 
        folder: str = "uploads", 
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """フォルダ内のファイル一覧を取得"""
        if not self.blob_service_client:
            return []
        
        try:
            container_client = self.blob_service_client.get_container_client(
                self.container_name
            )
            
            blobs = container_client.list_blobs(
                name_starts_with=f"{folder}/",
                include=['metadata']
            )
            
            files = []
            for blob in blobs:
                if len(files) >= limit:
                    break
                
                files.append({
                    "name": blob.name.split('/')[-1],
                    "blob_name": blob.name,
                    "url": f"{container_client.url}/{blob.name}",
                    "size": blob.size,
                    "content_type": blob.content_settings.content_type if blob.content_settings else None,
                    "last_modified": blob.last_modified,
                    "metadata": blob.metadata or {}
                })
            
            return files
            
        except AzureError as e:
            logger.error(f"List files error: {e}")
            return []
    
    def get_file_info(self, filename: str, folder: str = "uploads") -> Optional[Dict[str, Any]]:
        """ファイル情報を取得"""
        if not self.blob_service_client:
            return None
        
        try:
            blob_name = f"{folder}/{filename}"
            blob_client = self.blob_service_client.get_blob_client(
                container=self.container_name,
                blob=blob_name
            )
            
            properties = blob_client.get_blob_properties()
            
            return {
                "name": filename,
                "blob_name": blob_name,
                "url": blob_client.url,
                "size": properties.size,
                "content_type": properties.content_settings.content_type,
                "last_modified": properties.last_modified,
                "metadata": properties.metadata or {},
                "etag": properties.etag
            }
            
        except ResourceNotFoundError:
            return None
        except AzureError as e:
            logger.error(f"Get file info error: {e}")
            return None

# シングルトンインスタンス
azure_storage = AzureStorageService()

# ヘルパー関数
async def upload_photo(file: UploadFile) -> Dict[str, Any]:
    """写真アップロードのヘルパー関数"""
    return await azure_storage.upload_file(
        file=file,
        folder="eco-photos",
        resize_image=True,
        max_width=1200,
        max_height=1200
    )

async def upload_avatar(file: UploadFile) -> Dict[str, Any]:
    """アバターアップロードのヘルパー関数"""
    return await azure_storage.upload_file(
        file=file,
        folder="avatars",
        resize_image=True,
        max_width=400,
        max_height=400
    )

def delete_photo(filename: str) -> bool:
    """写真削除のヘルパー関数"""
    return asyncio.run(
        azure_storage.delete_file(filename, "eco-photos")
    )

def get_photo_sas_url(filename: str, expires_in_hours: int = 24) -> Optional[str]:
    """写真のSAS URL取得ヘルパー関数"""
    return azure_storage.generate_sas_url(
        filename, "eco-photos", expires_in_hours
    )
"@ | Out-File -FilePath app\core\azure_storage.py -Encoding UTF8