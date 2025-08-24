from datetime import datetime
import jwt
import requests

from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from database import SECRET_KEY, get_db

from .models import Base, User, Asset, Portfolio, Transaction
from .schemas import UserCreate, TradeAsset, AddMoney


app = FastAPI()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl='token')

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=["*"],
    allow_methods=["*"],
    allow_headers=["*"]

)


def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=['HS256']) 
        user = db.query(User).filter(User.username == payload['paylaod']).first()
        return user
    except:
        return HTTPException(status_code=401)