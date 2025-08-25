from datetime import datetime

import jwt
import requests

from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm

from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import sessionmaker, Session

from models import Base, User, Asset, Portfolio, Transaction
from schemas import UserCreate, AddMoney, TradeAsset

app = FastAPI()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl='token')

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=["*"],
    allow_methods=["*"],
    allow_headers=["*"]
)

engine = create_engine('sqlite:///./crypto_portfolio.db', connect_args={'check_same_thread': False})
insp = inspect(engine)

print(insp.get_table_names())
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base.metadata.create_all(bind=engine)

SECRET_KEY='some-key-but-not-this-one'


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
        if db.is_active:
            db.rollback()


def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=['HS256'])
        user = db.query(User).filter(User.username == payload['payload']).first()
        return user
    except:
        return HTTPException(status_code=401)


def get_crypto_price(symbol: str):
    try:
        response = requests.get(f'https://api.binance.com/api/v3/ticker/price?symbol={symbol}USDT')
        return float(response.json()['price'])
    except:
        return 0.0


@app.post('/register')
def register(user: UserCreate, db: Session = Depends(get_db)):
    db_user = User(username=user.username, password=user.password)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)

    portfolio = Portfolio(user_id=db_user.id)
    db.add(portfolio)
    db.commit()

    return {'message': 'Successfully created new user.'}