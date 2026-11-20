import pytest
from typing import Generator
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import settings
from app.core.database import Base, get_db
from app.core.security import create_access_token, get_password_hash
from app.main import app
from app.models.company import Company
from app.models.user import User

# Use in-memory SQLite database for fast, isolated tests
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="session", autouse=True)
def setup_test_db():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture()
def db() -> Generator:
    connection = engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)

    yield session

    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture()
def client(db) -> Generator:
    def override_get_db():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture()
def test_user(db) -> User:
    user = User(
        email="testcandidate@example.com",
        full_name="Alex Mercer",
        hashed_password=get_password_hash("SecretPassword123!"),
        resume_text=(
            "Experienced Python and FastAPI backend software engineer. "
            "Engineered scalable REST APIs, microservices, and PostgreSQL database models. "
            "Proficient in Docker, Git, CI/CD, and pytest unit testing. "
            "Improved system latency by 35% through query optimization."
        ),
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture()
def another_user(db) -> User:
    user = User(
        email="otherdeveloper@example.com",
        full_name="Jordan Lee",
        hashed_password=get_password_hash("AnotherPassword123!"),
        resume_text="Junior developer working with HTML, CSS, and basic JavaScript.",
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture()
def auth_headers(test_user) -> dict:
    token = create_access_token(subject=str(test_user.id))
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture()
def another_auth_headers(another_user) -> dict:
    token = create_access_token(subject=str(another_user.id))
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture()
def test_company(db) -> Company:
    company = Company(
        name="Stripe Tech",
        website="https://stripe.com",
        location="San Francisco, CA",
        industry="Financial Technology",
    )
    db.add(company)
    db.commit()
    db.refresh(company)
    return company
