from fastapi import FastAPI, Depends, HTTPException, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session
from contextlib import asynccontextmanager
import asyncio
from datetime import datetime

from database import get_db, StockDB
from models import StockCreate, StockResponse, PriceResponse
from stock_service import get_stock_price
from websocket_manager import manager

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: nothing special needed
    print("Starting stock tracker service...")
    yield
    # Shutdown: cleanup tasks (if any)
    print("Shutting down gracefully...")

app = FastAPI(title="Stock Tracker", lifespan=lifespan)

# -------------------- REST Endpoints --------------------
@app.get("/health")
async def health():
    """Health check for load balancers."""
    return {"status": "ok"}

@app.post("/stocks", response_model=StockResponse)
def add_stock(stock: StockCreate, db: Session = Depends(get_db)):
    """Add a ticker to watchlist."""
    symbol = stock.symbol.upper()
    existing = db.query(StockDB).filter(StockDB.symbol == symbol).first()
    if existing:
        raise HTTPException(status_code=400, detail="Stock already in watchlist")
    db_stock = StockDB(symbol=symbol, name=stock.name)
    db.add(db_stock)
    db.commit()
    db.refresh(db_stock)
    return db_stock

@app.delete("/stocks/{symbol}")
def delete_stock(symbol: str, db: Session = Depends(get_db)):
    """Remove a ticker from watchlist."""
    symbol = symbol.upper()
    stock = db.query(StockDB).filter(StockDB.symbol == symbol).first()
    if not stock:
        raise HTTPException(status_code=404, detail="Stock not found")
    db.delete(stock)
    db.commit()
    return {"message": f"{symbol} removed"}

@app.get("/stocks", response_model=list[StockResponse])
def list_stocks(db: Session = Depends(get_db)):
    """List all tracked tickers."""
    stocks = db.query(StockDB).all()
    return stocks

@app.get("/stocks/{symbol}/price", response_model=PriceResponse)
async def get_price(symbol: str, force: bool = False):
    """Get current price for a ticker (cached unless force=True)."""
    symbol = symbol.upper()
    price = await get_stock_price(symbol, force_refresh=force)
    if price is None:
        raise HTTPException(status_code=404, detail="Price not available")
    return PriceResponse(
        symbol=symbol,
        price=price,
        timestamp=datetime.utcnow(),
        cached=(not force and symbol in price_cache)
    )

# -------------------- WebSocket --------------------
@app.websocket("/ws/{symbol}")
async def websocket_endpoint(websocket: WebSocket, symbol: str):
    symbol = symbol.upper()
    await manager.connect(websocket, symbol)
    try:
        # Send initial price immediately
        price = await get_stock_price(symbol)
        if price:
            await websocket.send_text(f"{price:.2f}")
        # Then send updates every 5 seconds
        while True:
            await asyncio.sleep(5)
            price = await get_stock_price(symbol)  # uses cache
            if price:
                await manager.broadcast_price(symbol, price)
    except WebSocketDisconnect:
        manager.disconnect(websocket, symbol)