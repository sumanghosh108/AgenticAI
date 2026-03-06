"""
Database configuration for the Autonomous Research Report Generator.

- PostgreSQL via SQLAlchemy
- User model with hashlib-based password hashing
"""

import hashlib
import os
from datetime import datetime

from dotenv import load_dotenv
from sqlalchemy import Column, Integer, String, DateTime, create_engine, inspect
from sqlalchemy.orm import sessionmaker, declarative_base

from research_and_analyst.logger import GLOBAL_LOGGER as log
from research_and_analyst.exception.custom_exception import ResearchAnalystException

load_dotenv()

# ─────────────────────────────────────────────
# Engine & Session
# ─────────────────────────────────────────────

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:Admin@localhost:5432/AgenticAI",
)

engine = create_engine(DATABASE_URL, echo=False)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


# ─────────────────────────────────────────────
# User Model
# ─────────────────────────────────────────────

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    username = Column(String(100), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password = Column(String(256), nullable=False)
    age = Column(Integer, nullable=True)
    gender = Column(String(20), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<User(id={self.id}, username={self.username}, email={self.email})>"


# ─────────────────────────────────────────────
# Password Utilities (hashlib)
# ─────────────────────────────────────────────

SALT = os.getenv("PASSWORD_SALT", "agenticai_salt_2026")


def hash_password(password: str) -> str:
    """Hash a password using SHA-256 with a salt."""
    salted = f"{SALT}{password}"
    return hashlib.sha256(salted.encode("utf-8")).hexdigest()


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain password against a stored hash."""
    return hash_password(plain_password) == hashed_password


# ─────────────────────────────────────────────
# Table Creation
# ─────────────────────────────────────────────

def create_tables():
    """Create tables if they don't exist, otherwise validate."""
    try:
        inspector = inspect(engine)
        existing_tables = inspector.get_table_names()
        required_tables = Base.metadata.tables.keys()

        missing = [t for t in required_tables if t not in existing_tables]

        if missing:
            Base.metadata.create_all(bind=engine)
            log.info("Database tables created", tables=missing, url=DATABASE_URL.split("@")[-1])
        else:
            log.info("Database tables validated — all exist", tables=list(required_tables))
    except Exception as e:
        log.error("Failed to initialise database tables", error=str(e))
        raise ResearchAnalystException("Database table initialisation failed", e)


# ─────────────────────────────────────────────
# Standalone Test
# ─────────────────────────────────────────────

if __name__ == "__main__":
    create_tables()
    print("✅ Database tables created successfully")

    # Quick test: create a user
    session = SessionLocal()
    try:
        test_pw = hash_password("testpass")
        print(f"   Hash of 'testpass': {test_pw[:20]}...")
        print(f"   Verify correct:     {verify_password('testpass', test_pw)}")
        print(f"   Verify wrong:       {verify_password('wrong', test_pw)}")
    finally:
        session.close()
