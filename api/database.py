"""Connexion à PostgreSQL avec SQLAlchemy 2."""

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from api.config import DATABASE_URL

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
)

SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    """Classe de base commune aux modèles SQLAlchemy."""
    pass


def get_db():
    """Injecte une session puis la ferme après la requête."""

    db = SessionLocal()

    try:
        yield db
    finally:
        db.close()
