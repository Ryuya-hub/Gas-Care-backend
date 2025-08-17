@"
from sqlalchemy import create_engine, MetaData
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool
from app.config import settings
import logging

logger = logging.getLogger(__name__)

# SQLAlchemy Engine設定
if settings.database_url.startswith("sqlite"):
    # SQLite用の設定
    engine = create_engine(
        settings.database_url,
        connect_args={
            "check_same_thread": False,
            "timeout": 20
        },
        poolclass=StaticPool,
        echo=settings.DEBUG
    )
else:
    # PostgreSQL用の設定
    engine = create_engine(
        settings.database_url,
        pool_pre_ping=True,
        pool_recycle=300,
        echo=settings.DEBUG
    )

# Session作成
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

# Base クラス
Base = declarative_base()

# メタデータ設定
metadata = MetaData()

def get_db() -> Session:
    """
    データベースセッションを取得するDependency
    """
    db = SessionLocal()
    try:
        yield db
    except Exception as e:
        logger.error(f"Database session error: {e}")
        db.rollback()
        raise
    finally:
        db.close()

def create_tables():
    """
    テーブルを作成
    """
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables created successfully")
    except Exception as e:
        logger.error(f"Error creating database tables: {e}")
        raise

def drop_tables():
    """
    テーブルを削除（開発・テスト用）
    """
    try:
        Base.metadata.drop_all(bind=engine)
        logger.info("Database tables dropped successfully")
    except Exception as e:
        logger.error(f"Error dropping database tables: {e}")
        raise

def get_db_info():
    """
    データベース情報を取得
    """
    return {
        "database_url": settings.database_url.split("@")[-1] if "@" in settings.database_url else settings.database_url,
        "engine_name": engine.name,
        "pool_size": engine.pool.size() if hasattr(engine.pool, 'size') else "N/A",
        "echo": engine.echo
    }
"@ | Out-File -FilePath app\database.py -Encoding UTF8