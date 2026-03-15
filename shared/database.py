from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


def get_engine(database_url: str):
    return create_engine(database_url, pool_pre_ping=True)


def get_session_factory(engine):
    return sessionmaker(autocommit=False, autoflush=False, bind=engine)
