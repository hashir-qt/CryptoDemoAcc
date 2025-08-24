from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

engine = create_engine('sqlite:///./crypto_portfolio.db', connect_args={'check_same_thread': False}) 
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

SECRET_KEY='this-is-a-secret-key'


def get_db():
    db = SessionLocal
    try:
        yield db
    finally:
        db.close()
        if db.is_active:
            db.rollback()