@"
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, Union
from jose import JWTError, jwt
from passlib.context import CryptContext
from passlib.hash import bcrypt
from fastapi import HTTPException, status, Depends
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
import secrets
import string
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import smtplib
import logging

from app.config import settings
from app.database import get_db
from app.models.user import User

logger = logging.getLogger(__name__)

# パスワードハッシュ化設定
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# OAuth2設定
oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl=f"{settings.API_V1_STR}/auth/login",
    scopes={
        "read": "Read access",
        "write": "Write access",
        "admin": "Admin access"
    }
)

class SecurityUtils:
    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """パスワードの検証"""
        try:
            return pwd_context.verify(plain_password, hashed_password)
        except Exception as e:
            logger.error(f"Password verification error: {e}")
            return False
    
    @staticmethod
    def get_password_hash(password: str) -> str:
        """パスワードのハッシュ化"""
        return pwd_context.hash(password)
    
    @staticmethod
    def generate_random_string(length: int = 32) -> str:
        """ランダム文字列生成"""
        characters = string.ascii_letters + string.digits
        return ''.join(secrets.choice(characters) for _ in range(length))
    
    @staticmethod
    def generate_reset_token() -> str:
        """パスワードリセット用トークン生成"""
        return secrets.token_urlsafe(32)
    
    @staticmethod
    def validate_password_strength(password: str) -> Dict[str, Any]:
        """パスワード強度チェック"""
        result = {
            "is_valid": True,
            "issues": [],
            "score": 0
        }
        
        if len(password) < 8:
            result["issues"].append("パスワードは8文字以上である必要があります")
            result["is_valid"] = False
        else:
            result["score"] += 1
        
        if not any(c.islower() for c in password):
            result["issues"].append("小文字を含む必要があります")
            result["is_valid"] = False
        else:
            result["score"] += 1
        
        if not any(c.isupper() for c in password):
            result["issues"].append("大文字を含む必要があります")
            result["is_valid"] = False
        else:
            result["score"] += 1
        
        if not any(c.isdigit() for c in password):
            result["issues"].append("数字を含む必要があります")
            result["is_valid"] = False
        else:
            result["score"] += 1
        
        if not any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in password):
            result["issues"].append("特殊文字を含むことを推奨します")
        else:
            result["score"] += 1
        
        return result

class JWTManager:
    @staticmethod
    def create_access_token(
        data: Dict[str, Any], 
        expires_delta: Optional[timedelta] = None
    ) -> str:
        """アクセストークン作成"""
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        
        to_encode.update({"exp": expire, "type": "access"})
        encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
        return encoded_jwt
    
    @staticmethod
    def create_refresh_token(
        data: Dict[str, Any], 
        expires_delta: Optional[timedelta] = None
    ) -> str:
        """リフレッシュトークン作成"""
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=settings.REFRESH_TOKEN_EXPIRE_MINUTES)
        
        to_encode.update({"exp": expire, "type": "refresh"})
        encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
        return encoded_jwt
    
    @staticmethod
    def verify_token(token: str, token_type: str = "access") -> Optional[Dict[str, Any]]:
        """トークン検証"""
        try:
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
            if payload.get("type") != token_type:
                return None
            return payload
        except JWTError as e:
            logger.error(f"JWT verification error: {e}")
            return None
    
    @staticmethod
    def get_user_from_token(token: str, db: Session) -> Optional[User]:
        """トークンからユーザー情報取得"""
        payload = JWTManager.verify_token(token)
        if payload is None:
            return None
        
        username: str = payload.get("sub")
        if username is None:
            return None
        
        user = db.query(User).filter(User.username == username).first()
        return user

class AuthenticationService:
    def __init__(self, db: Session):
        self.db = db
    
    def authenticate_user(self, username: str, password: str) -> Optional[User]:
        """ユーザー認証"""
        user = self.db.query(User).filter(
            (User.username == username) | (User.email == username)
        ).first()
        
        if not user:
            return None
        
        if not SecurityUtils.verify_password(password, user.hashed_password):
            return None
        
        if not user.is_active:
            return None
        
        # ログイン時刻を更新
        user.last_login = datetime.utcnow()
        self.db.commit()
        
        return user
    
    def create_user_tokens(self, user: User) -> Dict[str, Any]:
        """ユーザーのトークン作成"""
        access_token = JWTManager.create_access_token(
            data={"sub": user.username, "user_id": user.id}
        )
        refresh_token = JWTManager.create_refresh_token(
            data={"sub": user.username, "user_id": user.id}
        )
        
        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
        }
    
    def refresh_access_token(self, refresh_token: str) -> Optional[Dict[str, Any]]:
        """アクセストークンのリフレッシュ"""
        payload = JWTManager.verify_token(refresh_token, "refresh")
        if payload is None:
            return None
        
        username = payload.get("sub")
        user_id = payload.get("user_id")
        
        if username is None or user_id is None:
            return None
        
        # ユーザーの存在確認
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user or not user.is_active:
            return None
        
        # 新しいアクセストークンを作成
        access_token = JWTManager.create_access_token(
            data={"sub": username, "user_id": user_id}
        )
        
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
        }

# Dependency関数
async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> User:
    """現在のユーザーを取得"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="認証情報を確認できませんでした",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        username: str = payload.get("sub")
        user_id: int = payload.get("user_id")
        if username is None or user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise credentials_exception
    
    return user

async def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """アクティブなユーザーを取得"""
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="非アクティブなユーザーです"
        )
    return current_user

async def get_current_admin_user(
    current_user: User = Depends(get_current_active_user)
) -> User:
    """管理者ユーザーを取得"""
    # TODO: 管理者権限の実装
    # 現在は全ユーザーを管理者として扱う（開発用）
    return current_user

def require_permissions(required_permissions: list):
    """権限チェックデコレータ"""
    def decorator(func):
        async def wrapper(*args, current_user: User = Depends(get_current_active_user), **kwargs):
            # TODO: 権限システムの実装
            # 現在は全てのアクティブユーザーに権限を付与（開発用）
            return await func(*args, current_user=current_user, **kwargs)
        return wrapper
    return decorator

class EmailService:
    """メール送信サービス"""
    
    @staticmethod
    def send_verification_email(email: str, token: str) -> bool:
        """確認メール送信"""
        if not settings.SMTP_HOST:
            logger.warning("SMTP not configured, skipping email verification")
            return True
        
        try:
            # TODO: メール送信の実装
            logger.info(f"Verification email would be sent to {email} with token {token}")
            return True
        except Exception as e:
            logger.error(f"Failed to send verification email: {e}")
            return False
    
    @staticmethod
    def send_password_reset_email(email: str, token: str) -> bool:
        """パスワードリセットメール送信"""
        if not settings.SMTP_HOST:
            logger.warning("SMTP not configured, skipping password reset email")
            return True
        
        try:
            # TODO: メール送信の実装
            logger.info(f"Password reset email would be sent to {email} with token {token}")
            return True
        except Exception as e:
            logger.error(f"Failed to send password reset email: {e}")
            return False
"@ | Out-File -FilePath app\core\security.py -Encoding UTF8