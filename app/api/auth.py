@"
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from datetime import timedelta
import logging

from app.database import get_db
from app.models.user import User
from app.schemas.user import (
    UserCreate, UserResponse, Token, RefreshTokenRequest,
    LoginRequest, EmailVerificationRequest, PasswordResetRequest,
    PasswordResetConfirm
)
from app.core.security import (
    SecurityUtils, AuthenticationService, EmailService,
    get_current_user, get_current_active_user
)
from app.utils.helpers import validate_email, validate_username
from app.config import settings

logger = logging.getLogger(__name__)
router = APIRouter()

@router.post("/register", response_model=Token, status_code=status.HTTP_201_CREATED)
async def register(user_data: UserCreate, db: Session = Depends(get_db)):
    """
    ユーザー登録
    """
    # メールアドレスの重複チェック
    existing_user = db.query(User).filter(User.email == user_data.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="このメールアドレスは既に登録されています"
        )
    
    # ユーザー名の重複チェック
    existing_username = db.query(User).filter(User.username == user_data.username).first()
    if existing_username:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="このユーザー名は既に使用されています"
        )
    
    # ユーザー名検証
    username_validation = validate_username(user_data.username)
    if not username_validation["is_valid"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=", ".join(username_validation["issues"])
        )
    
    # パスワード強度チェック
    password_validation = SecurityUtils.validate_password_strength(user_data.password)
    if not password_validation["is_valid"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=", ".join(password_validation["issues"])
        )
    
    # ユーザー作成
    hashed_password = SecurityUtils.get_password_hash(user_data.password)
    
    db_user = User(
        email=user_data.email,
        username=user_data.username,
        hashed_password=hashed_password,
        full_name=user_data.full_name,
        bio=user_data.bio,
        location=user_data.location,
        is_public_profile=user_data.is_public_profile,
        notification_enabled=user_data.notification_enabled
    )
    
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    
    # メール認証送信（実装済みの場合）
    try:
        verification_token = SecurityUtils.generate_reset_token()
        EmailService.send_verification_email(db_user.email, verification_token)
    except Exception as e:
        logger.warning(f"Failed to send verification email: {e}")
    
    # JWT トークン生成
    auth_service = AuthenticationService(db)
    tokens = auth_service.create_user_tokens(db_user)
    
    return {
        **tokens,
        "user": db_user
    }

@router.post("/login", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    """
    ログイン（OAuth2PasswordRequestForm対応）
    """
    auth_service = AuthenticationService(db)
    user = auth_service.authenticate_user(form_data.username, form_data.password)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="メールアドレス/ユーザー名またはパスワードが正しくありません",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    tokens = auth_service.create_user_tokens(user)
    
    return {
        **tokens,
        "user": user
    }

@router.post("/login-json", response_model=Token)
async def login_json(login_data: LoginRequest, db: Session = Depends(get_db)):
    """
    ログイン（JSON形式）
    """
    auth_service = AuthenticationService(db)
    user = auth_service.authenticate_user(login_data.username, login_data.password)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="メールアドレス/ユーザー名またはパスワードが正しくありません",
        )
    
    tokens = auth_service.create_user_tokens(user)
    
    return {
        **tokens,
        "user": user
    }

@router.post("/refresh", response_model=dict)
async def refresh_token(refresh_data: RefreshTokenRequest, db: Session = Depends(get_db)):
    """
    アクセストークンのリフレッシュ
    """
    auth_service = AuthenticationService(db)
    new_tokens = auth_service.refresh_access_token(refresh_data.refresh_token)
    
    if not new_tokens:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="無効なリフレッシュトークンです",
        )
    
    return new_tokens

@router.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user: User = Depends(get_current_active_user)):
    """
    現在のユーザー情報取得
    """
    return current_user

@router.post("/logout")
async def logout(current_user: User = Depends(get_current_active_user)):
    """
    ログアウト
    注意: JWTはステートレスのため、実際のトークン無効化はクライアント側で行う
    """
    return {"message": "正常にログアウトしました"}

@router.post("/verify-email")
async def request_email_verification(
    request: EmailVerificationRequest, 
    db: Session = Depends(get_db)
):
    """
    メール認証の要求
    """
    user = db.query(User).filter(User.email == request.email).first()
    if not user:
        # セキュリティ上、存在しないメールアドレスでも成功のレスポンスを返す
        return {"message": "認証メールを送信しました"}
    
    if user.is_email_verified:
        return {"message": "メールアドレスは既に認証済みです"}
    
    # 認証トークン生成・送信
    verification_token = SecurityUtils.generate_reset_token()
    
    try:
        EmailService.send_verification_email(user.email, verification_token)
        return {"message": "認証メールを送信しました"}
    except Exception as e:
        logger.error(f"Failed to send verification email: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="メール送信に失敗しました"
        )

@router.post("/verify-email/{token}")
async def verify_email(token: str, db: Session = Depends(get_db)):
    """
    メール認証の実行
    """
    # TODO: トークンの検証とメール認証処理
    # 現在は全てのトークンを有効として扱う（開発用）
    
    return {"message": "メールアドレスが認証されました"}

@router.post("/forgot-password")
async def forgot_password(request: PasswordResetRequest, db: Session = Depends(get_db)):
    """
    パスワードリセットの要求
    """
    user = db.query(User).filter(User.email == request.email).first()
    
    # セキュリティ上、存在しないメールアドレスでも成功のレスポンスを返す
    if user:
        reset_token = SecurityUtils.generate_reset_token()
        
        try:
            EmailService.send_password_reset_email(user.email, reset_token)
        except Exception as e:
            logger.error(f"Failed to send password reset email: {e}")
    
    return {"message": "パスワードリセット用のメールを送信しました"}

@router.post("/reset-password")
async def reset_password(request: PasswordResetConfirm, db: Session = Depends(get_db)):
    """
    パスワードリセットの実行
    """
    # TODO: トークンの検証処理
    # 現在は全てのトークンを有効として扱う（開発用）
    
    # パスワード強度チェック
    password_validation = SecurityUtils.validate_password_strength(request.new_password)
    if not password_validation["is_valid"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=", ".join(password_validation["issues"])
        )
    
    # TODO: トークンからユーザーを特定してパスワードを更新
    # 現在は仮の実装
    
    return {"message": "パスワードがリセットされました"}

@router.get("/check-username/{username}")
async def check_username_availability(username: str, db: Session = Depends(get_db)):
    """
    ユーザー名の利用可能性チェック
    """
    # ユーザー名の形式チェック
    validation = validate_username(username)
    if not validation["is_valid"]:
        return {
            "available": False,
            "reason": "invalid_format",
            "issues": validation["issues"]
        }
    
    # 重複チェック
    existing_user = db.query(User).filter(User.username == username).first()
    if existing_user:
        return {
            "available": False,
            "reason": "already_taken"
        }
    
    return {
        "available": True,
        "username": username
    }

@router.get("/check-email/{email}")
async def check_email_availability(email: str, db: Session = Depends(get_db)):
    """
    メールアドレスの利用可能性チェック
    """
    # メールアドレスの形式チェック
    if not validate_email(email):
        return {
            "available": False,
            "reason": "invalid_format"
        }
    
    # 重複チェック
    existing_user = db.query(User).filter(User.email == email).first()
    if existing_user:
        return {
            "available": False,
            "reason": "already_taken"
        }
    
    return {
        "available": True,
        "email": email
    }

@router.get("/validate-token")
async def validate_token(current_user: User = Depends(get_current_user)):
    """
    トークンの有効性確認
    """
    return {
        "valid": True,
        "user_id": current_user.id,
        "username": current_user.username,
        "is_active": current_user.is_active
    }

@router.get("/session-info")
async def get_session_info(current_user: User = Depends(get_current_active_user)):
    """
    セッション情報取得
    """
    return {
        "user": {
            "id": current_user.id,
            "username": current_user.username,
            "email": current_user.email,
            "full_name": current_user.full_name,
            "avatar_url": current_user.avatar_url,
            "level": current_user.level,
            "total_points": current_user.total_points
        },
        "session": {
            "last_login": current_user.last_login,
            "is_email_verified": current_user.is_email_verified,
            "is_active": current_user.is_active
        },
        "permissions": {
            "can_read": True,
            "can_write": True,
            "can_upload": True,
            "can_admin": False  # TODO: 権限システム実装後に更新
        }
    }
"@ | Out-File -FilePath app\api\auth.py -Encoding UTF8