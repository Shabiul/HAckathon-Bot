import os
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, scoped_session, sessionmaker

class Base(DeclarativeBase):
    pass

# Configure SQLAlchemy
DATABASE_URL = os.environ.get("DATABASE_URL")
if DATABASE_URL:
    engine = create_engine(DATABASE_URL)
    db_session = scoped_session(sessionmaker(bind=engine))
    Base.query = db_session.query_property()
else:
    raise ValueError("DATABASE_URL environment variable is not set")

# Import models to ensure they're registered
import models  # noqa: F401

# Create all tables
Base.metadata.create_all(bind=engine)