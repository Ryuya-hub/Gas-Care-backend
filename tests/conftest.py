"""
Test configuration and fixtures for We Planet backend tests.
"""
import pytest
import asyncio
from httpx import AsyncClient
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, patch
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.core.database import get_db, Base
from app.core.auth import create_access_token, get_current_user
from app.models.user import User
from app.models.family import Family

# Test database setup
SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def override_get_db():
    """Override database dependency for testing."""
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

# Override the database dependency
app.dependency_overrides[get_db] = override_get_db

@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture
def client():
    """Create a test client."""
    Base.metadata.create_all(bind=engine)
    with TestClient(app) as test_client:
        yield test_client
    Base.metadata.drop_all(bind=engine)

@pytest.fixture
async def async_client():
    """Create an async test client."""
    Base.metadata.create_all(bind=engine)
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac
    Base.metadata.drop_all(bind=engine)

@pytest.fixture
def test_user():
    """Create a test user."""
    return {
        "id": 1,
        "username": "testuser",
        "email": "test@example.com",
        "password": "testpassword123"
    }

@pytest.fixture
def test_family():
    """Create a test family."""
    return {
        "id": 1,
        "name": "Test Family",
        "description": "A family for testing",
        "created_by": 1
    }

@pytest.fixture
def auth_headers(test_user):
    """Create authentication headers with JWT token."""
    token = create_access_token(data={"sub": str(test_user["id"])})
    return {"Authorization": f"Bearer {token}"}

@pytest.fixture
def mock_db():
    """Create a mock database session."""
    return MagicMock()

@pytest.fixture
def mock_azure_storage():
    """Mock Azure Blob Storage client."""
    with patch("app.core.azure_storage.BlobServiceClient") as mock:
        yield mock

@pytest.fixture
def mock_current_user(test_user):
    """Mock current authenticated user."""
    user_obj = User(**test_user)
    with patch("app.core.auth.get_current_user", return_value=user_obj):
        yield user_obj
