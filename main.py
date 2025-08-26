from datetime import datetime

import jwt
import requests

from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.responses import StreamingResponse

from sqlalchemy import create_engine
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

db_engine = create_engine('sqlite:///./crypto_portfolio.db', connect_args={'check_same_thread': False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=db_engine)
Base.metadata.create_all(bind=db_engine)


SECRET_KEY='just-one-of-my-secret-keys'


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
        user = db.query(User).filter(User.username == payload['username']).first()
        if not user:
            raise HTTPException(status_code=401, detail="Invalid token")
        return user
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")
    except Exception as e:
        raise HTTPException(status_code=401, detail="Authentication failed")


def get_crypto_price(symbol: str):
    try:
        response = requests.get(f'https://api.binance.com/api/v3/ticker/price?symbol={symbol}USDT')
        response.raise_for_status()  # Raise exception for bad status codes
        data = response.json()
        if 'price' not in data:
            return 0.0
        return float(data['price'])
    except requests.RequestException:
        return 0.0
    except (ValueError, KeyError):
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


@app.post('/login')
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):

    user = db.query(User).filter(User.username == form_data.username).first()

    if not user or user.password != form_data.password:
        raise HTTPException(status_code=400, detail='Information invalid')

    token = jwt.encode({'username': user.username}, SECRET_KEY, algorithms=['HS256'])

    return {'access_token': token, 'token_type': 'bearer'}




@app.post('/add-money')
def add_money(money: AddMoney, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if money.amount <= 0:
        raise HTTPException(status_code=400, detail="Amount must be positive")

    try:
        portfolio = user.portfolio
        portfolio.total_added_money += money.amount
        portfolio.available_money += money.amount

        db.commit()
        return {'message': 'Successfully added money to your account'}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to add money")


@app.post('/buy')
def buy_asset(trade: TradeAsset, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if not trade.symbol or trade.quantity <= 0:
        raise HTTPException(status_code=400, detail="Invalid symbol or quantity")

    try:
        portfolio = user.portfolio
        price = get_crypto_price(trade.symbol)
        
        if price <= 0:
            raise HTTPException(status_code=400, detail="Unable to get current price for this asset")
            
        total_cost = price * trade.quantity

        if total_cost > portfolio.available_money:
            raise HTTPException(status_code=400, detail='Insufficient funds')

        asset = db.query(Asset).filter(Asset.portfolio_id == portfolio.id, Asset.symbol == trade.symbol).first()

        if asset:
            asset.quantity += trade.quantity
        else:
            asset = Asset(portfolio_id=portfolio.id, symbol=trade.symbol, quantity=trade.quantity)
            db.add(asset)

        transaction = Transaction(portfolio_id=portfolio.id, symbol=trade.symbol, quantity=trade.quantity, price=price, timestamp=datetime.utcnow())
        db.add(transaction)
        portfolio.available_money -= total_cost
        db.commit()

        return {'message': 'Asset successfully bought.'}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to buy asset")



@app.post('/sell')
def sell_asset(trade: TradeAsset, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if not trade.symbol or trade.quantity <= 0:
        raise HTTPException(status_code=400, detail="Invalid symbol or quantity")

    try:
        portfolio = user.portfolio
        asset = db.query(Asset).filter(Asset.portfolio_id == portfolio.id, Asset.symbol == trade.symbol).first()

        if not asset or asset.quantity < trade.quantity:
            raise HTTPException(status_code=400, detail='Not enough to sell')

        price = get_crypto_price(trade.symbol)
        
        if price <= 0:
            raise HTTPException(status_code=400, detail="Unable to get current price for this asset")
            
        total_value = price * trade.quantity

        asset.quantity -= trade.quantity

        if asset.quantity == 0:
            db.delete(asset)

        transaction = Transaction(portfolio_id=portfolio.id, symbol=trade.symbol, quantity=-trade.quantity, price=price, timestamp=datetime.utcnow())
        db.add(transaction)

        portfolio.available_money += total_value

        db.commit()

        return {'message': 'Asset successfully sold.'}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to sell asset")


@app.get('/portfolio')
def get_portfolio(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    try:
        portfolio = user.portfolio

        assets_response = []
        total_value = portfolio.available_money

        for asset in portfolio.assets:
            current_price = get_crypto_price(asset.symbol)
            net_quantity = asset.quantity
            asset_value = current_price * net_quantity
            total_value += asset_value
            transactions = db.query(Transaction).filter(Transaction.portfolio_id == portfolio.id, Transaction.symbol == asset.symbol).all()

            total_cost = 0
            total_bought = 0

            for t in transactions:
                if t.quantity > 0:
                    total_cost += t.quantity * t.price
                    total_bought += t.quantity

            avg_purchase_price = total_cost / total_bought if total_bought > 0 else 0
            invested_amount = avg_purchase_price * net_quantity

            assets_response.append({
                'symbol': asset.symbol,
                'quantity': asset.quantity,
                'current_price': current_price,
                'total_value': asset_value,
                'avg_purchase_price': avg_purchase_price,
                'performance_abs': asset_value - invested_amount,
                'performance_rel': (asset_value - invested_amount) / invested_amount * 100 if invested_amount != 0 else 0
            })

        return {
            'total_added_money': portfolio.total_added_money,
            'available_money': portfolio.available_money,
            'total_value': total_value,
            'performance_abs': total_value - portfolio.total_added_money,
            'performance_rel': (total_value - portfolio.total_added_money) / portfolio.total_added_money * 100 if portfolio.total_added_money != 0 else 0,
            'assets': assets_response
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to fetch portfolio")


@app.get('/stream-prices')
async def stream_prices(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Stream real-time price updates for user's portfolio assets"""
    
    async def generate_price_stream():
        import asyncio
        import json
        
        try:
            portfolio = user.portfolio
            while True:
                # Get current prices for all assets in portfolio
                price_updates = {}
                total_value = portfolio.available_money
                
                for asset in portfolio.assets:
                    current_price = get_crypto_price(asset.symbol)
                    asset_value = current_price * asset.quantity
                    total_value += asset_value
                    
                    # Calculate performance
                    transactions = db.query(Transaction).filter(
                        Transaction.portfolio_id == portfolio.id, 
                        Transaction.symbol == asset.symbol
                    ).all()
                    
                    total_cost = 0
                    total_bought = 0
                    
                    for t in transactions:
                        if t.quantity > 0:
                            total_cost += t.quantity * t.price
                            total_bought += t.quantity
                    
                    avg_purchase_price = total_cost / total_bought if total_bought > 0 else 0
                    invested_amount = avg_purchase_price * asset.quantity
                    performance_abs = asset_value - invested_amount
                    performance_rel = (asset_value - invested_amount) / invested_amount * 100 if invested_amount != 0 else 0
                    
                    price_updates[asset.symbol] = {
                        'current_price': current_price,
                        'total_value': asset_value,
                        'performance_abs': performance_abs,
                        'performance_rel': performance_rel
                    }
                
                # Calculate overall portfolio performance
                portfolio_performance_abs = total_value - portfolio.total_added_money
                portfolio_performance_rel = (total_value - portfolio.total_added_money) / portfolio.total_added_money * 100 if portfolio.total_added_money != 0 else 0
                
                # Send price updates
                data = {
                    'timestamp': datetime.utcnow().isoformat(),
                    'total_value': total_value,
                    'portfolio_performance_abs': portfolio_performance_abs,
                    'portfolio_performance_rel': portfolio_performance_rel,
                    'assets': price_updates
                }
                
                yield f"data: {json.dumps(data)}\n\n"
                
                # Wait 10 seconds before next update
                await asyncio.sleep(10)
                
        except Exception as e:
            yield f"data: {json.dumps({'error': 'Stream failed'})}\n\n"
    
    return StreamingResponse(
        generate_price_stream(),
        media_type="text/plain",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Content-Type": "text/event-stream"
        }
    )