# 🚀 Crypto Portfolio Manager Backend (FastAPI)

This is the **backend service** for the Crypto Portfolio Manager app.  
The **frontend** is built with [Next.js (App Router)](https://nextjs.org/), while the backend is powered by [FastAPI](https://fastapi.tiangolo.com/).

## 📌 Features

- 🔐 **JWT Authentication** – User registration & login
- 💰 **Money Management** – Add funds, manage balance
- 📊 **Portfolio Tracking** – View assets & total valuation
- 💱 **Trading System** – Buy & sell assets with validation
- 📡 **Real-time Prices** – Fetch live crypto prices via **Binance API**
- ⚡ **Event Streaming** – Real-time portfolio updates using **Server-Sent Events (SSE)**

---

## 🛠️ Tech Stack

- [FastAPI](https://fastapi.tiangolo.com/) – Backend framework
- [SQLite](https://www.sqlite.org/) – Local development DB (will migrate to **PostgreSQL** 🗄️)
- [Pydantic](https://docs.pydantic.dev/) – Data validation
- [JWT (PyJWT)](https://pyjwt.readthedocs.io/) – Authentication
- [Binance API](https://binance-docs.github.io/apidocs/) – Live crypto data

---

## 📂 Project Structure

backend/
├── app/
│ ├── main.py # FastAPI entrypoint
│ ├── models.py # Database models
│ ├── schemas.py # Pydantic schemas
├── requirements.txt # Python dependencies
└── README.md # Project documentation


---

## 🚀 Getting Started

### 1️⃣ Clone the repository
```bash
git clone https://github.com/your-username/crypto-portfolio-backend.git
cd crypto-portfolio-backend

2️⃣ Create virtual environment
python -m venv venv
source venv/bin/activate   # Linux / macOS
venv\Scripts\activate      # Windows

3️⃣ Install dependencies
pip install -r requirements.txt

4️⃣ Run the server
uvicorn app.main:app --reload


Backend will be available at 👉 http://localhost:8000

📡 API Endpoints (Overview)
🔐 Authentication

POST /auth/register → Register new user

POST /auth/login → Login & get JWT

💰 Portfolio

GET /portfolio → Get user portfolio

POST /portfolio/add-money → Add money to balance

💱 Trading

POST /trade/buy → Buy an asset

POST /trade/sell → Sell an asset

📡 Real-time

GET /stream/updates → Server-Sent Events (live portfolio updates)