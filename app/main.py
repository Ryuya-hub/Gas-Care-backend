@"
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
import time
import logging
from contextlib import asynccontextmanager

from app.config import settings
from app.database import create_tables, get_db_info

# APIルーターのインポート
from app.api import auth, users, families, eco_activities, badges, dashboard, uploads

# ログ設定
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    アプリケーションのライフサイクル管理
    """
    # 起動時の処理
    logger.info(f"Starting {settings.PROJECT_NAME}")
    logger.info(f"Environment: {settings.ENVIRONMENT}")
    logger.info(f"Debug mode: {settings.DEBUG}")
    
    # データベーステーブル作成
    try:
        create_tables()
        db_info = get_db_info()
        logger.info(f"Database connected: {db_info}")
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        # 本番環境では起動を停止することも検討
    
    yield
    
    # 終了時の処理
    logger.info(f"Shutting down {settings.PROJECT_NAME}")

# FastAPIアプリケーション作成
app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description=settings.DESCRIPTION,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
    lifespan=lifespan
)

# セキュリティミドルウェア
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=["*"] if settings.DEBUG else ["your-domain.com", "*.your-domain.com"]
)

# CORS設定
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["*"]
)

# リクエスト処理時間ミドルウェア
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    return response

# エラーハンドラー
@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": True,
            "message": exc.detail,
            "status_code": exc.status_code,
            "timestamp": time.time()
        }
    )

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=422,
        content={
            "error": True,
            "message": "Validation error",
            "details": exc.errors(),
            "status_code": 422,
            "timestamp": time.time()
        }
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": True,
            "message": "Internal server error" if not settings.DEBUG else str(exc),
            "status_code": 500,
            "timestamp": time.time()
        }
    )

# ルートエンドポイント
@app.get("/")
async def root():
    """
    ルートエンドポイント - API情報
    """
    return {
        "message": f"🌍 {settings.PROJECT_NAME}",
        "version": settings.VERSION,
        "status": "healthy",
        "environment": settings.ENVIRONMENT,
        "docs": "/docs" if settings.DEBUG else "Documentation disabled in production",
        "timestamp": time.time()
    }

@app.get("/health")
async def health_check():
    """
    ヘルスチェックエンドポイント
    """
    try:
        db_info = get_db_info()
        return {
            "status": "healthy",
            "environment": settings.ENVIRONMENT,
            "version": settings.VERSION,
            "database": db_info,
            "timestamp": time.time()
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(
            status_code=503,
            detail="Service temporarily unavailable"
        )

@app.get("/info")
async def app_info():
    """
    アプリケーション情報エンドポイント
    """
    return {
        "project_name": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "environment": settings.ENVIRONMENT,
        "debug": settings.DEBUG,
        "api_prefix": settings.API_V1_STR,
        "cors_origins": len(settings.ALLOWED_ORIGINS),
        "database_type": "PostgreSQL" if "postgresql" in settings.database_url else "SQLite",
        "features": {
            "authentication": True,
            "family_management": True,
            "eco_activities": True,
            "badge_system": True,
            "file_upload": True,
            "azure_storage": bool(settings.AZURE_STORAGE_CONNECTION_STRING)
        }
    }

# APIルーターの登録
app.include_router(
    auth.router,
    prefix=f"{settings.API_V1_STR}/auth",
    tags=["🔐 Authentication"]
)

app.include_router(
    users.router,
    prefix=f"{settings.API_V1_STR}/users",
    tags=["👤 Users"]
)

app.include_router(
    families.router,
    prefix=f"{settings.API_V1_STR}/families",
    tags=["👨‍👩‍👧‍👦 Families"]
)

app.include_router(
    eco_activities.router,
    prefix=f"{settings.API_V1_STR}/eco-activities",
    tags=["🌱 Eco Activities"]
)

app.include_router(
    badges.router,
    prefix=f"{settings.API_V1_STR}/badges",
    tags=["🏆 Badges & Missions"]
)

app.include_router(
    dashboard.router,
    prefix=f"{settings.API_V1_STR}/dashboard",
    tags=["📊 Dashboard"]
)

app.include_router(
    uploads.router,
    prefix=f"{settings.API_V1_STR}/uploads",
    tags=["📸 File Uploads"]
)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower()
    )
"@ | Out-File -FilePath app\main.py -Encoding UTF8