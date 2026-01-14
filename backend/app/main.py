import time
from fastapi import FastAPI, Depends, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel
import logging
import asyncio

from .storage import models, database
from .foxbit_client.client import FoxbitClient
from .paper_broker.broker import PaperBroker, Order
from .paper_broker.real_broker import RealBroker
from .risk_engine.engine import RiskEngine, TradeRisk
import os

# Setup Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("crypto_paper")

app = FastAPI(title="Crypto Paper Trading", version="1.0.0")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Allow all for local dev convenience
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Dependency
get_db = database.get_db

# Global State (In-memory for V1 simplicity of the simulation loop)
class GlobalSystemState:
    is_running = False
    broker = None # Initialized in __init__
    risk_engine = RiskEngine(TradeRisk())
    client = FoxbitClient()
    active_strategy = "StrategyA"
    logs: List[str] = [] # Last 50 logs
    last_price: float = 0.0
    last_update: float = 0.0
    health_metrics: dict = {}
    fatal_error: Optional[str] = None
    entry_price: float = 0.0 # Track average entry price

    def __init__(self):
        self.health_metrics = {}
        self.fatal_error = None
        
        # Initialize Broker based on Mode
        mode = os.getenv("TRADING_MODE", "PAPER").upper()
        if mode == "LIVE":
             logger.warning("🚨 SYSTEM STARTING IN LIVE TRADING MODE (BINANCE) 🚨")
             try:
                 self.broker = RealBroker()
             except Exception as e:
                 logger.critical(f"Failed to initialize RealBroker: {e}")
                 self.fatal_error = str(e)
                 self.broker = PaperBroker(initial_balance=120.0) # Fallback to prevent crash
        else:
             logger.info("ℹ️ System starting in PAPER TRADING mode.")
             self.broker = PaperBroker(initial_balance=120.0)

    def log(self, message: str, level: str = "INFO"):
        """Add log message to in-memory list"""
        timestamp = time.strftime("%H:%M:%S")
        entry = f"[{timestamp}] [{level}] {message}"
        self.logs.insert(0, entry) # Prepend
        if len(self.logs) > 50:
            self.logs.pop() # Keep size fixed
        # Also print to stdout
        if level == "ERROR" or level == "CRITICAL":
            logger.error(message)
        else:
            logger.info(message)

state = GlobalSystemState()

@app.on_event("startup")
def startup_event():
    models.Base.metadata.create_all(bind=database.engine)
    
    # Restore State from DB
    try:
        db = database.SessionLocal()
        last_trade = db.query(models.Trade).order_by(models.Trade.entered_at.desc()).first()
        if last_trade and last_trade.side == "buy" and last_trade.status == "filled":
             # Restore Holdings and Entry Price
             qty = float(last_trade.quantity)
             entry = float(last_trade.entry_price)
             cost = qty * entry
             
             state.entry_price = entry

             # Handling Logic based on Mode
             if isinstance(state.broker, RealBroker):
                 # LIVE MODE: Trust the Broker (Binance) for Balance/Holdings.
                 # Only restore Entry Price if we actually hold BTC.
                 if state.broker.holdings > 0:
                      logger.info(f"🔄 LIVE State Restored: Resuming Real Long Position. Entry: {entry} | Holdings: {state.broker.holdings} (Binance)")
                 else:
                      logger.warning(f"⚠️ State Mismatch: DB says bought at {entry}, but Binance Holdings are 0. Assuming FLAT.")
                      state.entry_price = 0.0 # Reset entry price as we have no position
             else:
                 # PAPER MODE: Restore Virtual State
                 state.broker.holdings = qty
                 # Fix Balance Mismatch: If balance is "Full" (e.g. 126) but we should be invested, deduct cost.
                 if state.broker.balance > (cost * 0.5):
                     state.broker.balance -= cost
                     logger.warning(f"⚠️ Adjusted Balance: Deducted {cost:.2f} BRL to match Open Position.")
                 logger.info(f"🔄 PAPER State Restored: Resuming Virtual Position. Entry: {entry} | Qty: {qty} | Bal: {state.broker.balance:.2f}")
        else:
             if last_trade:
                 logger.info(f"ℹ️ State Restoration Skipped: Last trade {last_trade.side} ({last_trade.status})")
             else:
                 logger.info("ℹ️ State Restoration Skipped: No trades found in DB.")
        db.close()
    except Exception as e:
        logger.error(f"Failed to restore state: {e}")

    # Start Market Data Loop
    asyncio.create_task(market_data_loop())

# --- API Models ---
class ConfigUpdate(BaseModel):
    max_position_size_pct: float
    stop_loss_pct: float
    max_drawdown_limit: float

class OrderRequest(BaseModel):
    symbol: str
    side: str
    quantity: float
    type: str = "market"

# --- Endpoints ---

@app.get("/")
async def read_root():
    return {"status": "ok", "service": "Crypto Paper Trader"}

@app.get("/api/status")
async def get_status():
    return {
        "running": state.is_running,
        "balance": state.broker.balance,
        "holdings": state.broker.holdings,
        "orders": len(state.broker.orders),
        "kill_switch": state.risk_engine.kill_switch_active,
        "logs": state.logs[:5],
        "current_price": state.last_price,
        "total_equity": state.broker.balance + (state.broker.holdings * state.last_price),
        "last_update": state.last_update,
        "health": state.health_metrics,
        "fatal_error": state.fatal_error,
        "db_type": "PostgreSQL (Supabase)" if "postgresql" in database.SQLALCHEMY_DATABASE_URL else "SQLite (Local)"
    }

@app.post("/api/start")
async def start_trading(background_tasks: BackgroundTasks):
    if state.risk_engine.kill_switch_active:
        raise HTTPException(status_code=400, detail="Kill switch active. Reset required.")
    
    if not state.is_running:
        state.is_running = True
        state.fatal_error = None # Reset error on manual start
        # state.risk_engine.set_balance(state.broker.balance) # Don't reset balance
        background_tasks.add_task(trading_loop)
    return {"message": "Paper trading started"}

@app.post("/api/stop")
async def stop_trading():
    state.is_running = False
    return {"message": "Paper trading stopped"}

@app.get("/api/history")
async def get_history():
    return state.broker.trade_history

@app.post("/api/config")
async def update_config(config: ConfigUpdate):
    state.risk_engine.config.max_position_size_pct = config.max_position_size_pct
    state.risk_engine.config.stop_loss_pct = config.stop_loss_pct
    state.risk_engine.config.max_drawdown_limit = config.max_drawdown_limit
    return {"message": "Config updated"}

# --- Background Tasks ---

async def market_data_loop():
    """Fetch market data continuously, regardless of trading status"""
    logger.info("Starting market data loop...")
    symbol = "btcbrl"
    
    while True:
        try:
            # Run blocking call in thread
            loop = asyncio.get_running_loop()
            # Reduce timeout to fail fast
            ticker = await loop.run_in_executor(None, lambda: state.client.get_ticker(symbol))
            
            if ticker and 'last' in ticker:
                 current_price = float(ticker['last'])
                 state.last_price = current_price
                 state.last_update = time.time()
                 
                 # Set health metric
                 if not hasattr(state, "health_metrics"): state.health_metrics = {}
                 state.health_metrics["market_api"] = "connected"
                 source = ticker.get("source", "Unknown")
                 if source in ["Binance", "MercadoBitcoin"]:
                      if int(time.time()) % 120 == 0:
                         logger.info(f"Price Feed active via {source} (Price: {current_price})")
                 
            else:
                 # Data fetch failed or returned invalid format
                 if not hasattr(state, "health_metrics"): state.health_metrics = {}
                 state.health_metrics["market_api"] = "error"

        except Exception as e:
            logger.error(f"Market loop error: {e}")
            if not hasattr(state, "health_metrics"): state.health_metrics = {}
            state.health_metrics["market_api"] = "disconnected"
        
        await asyncio.sleep(10) # Update price every 10s to stay under rate limits

async def trading_loop():
    logger.info("Starting trading loop...")
    symbol = "btcbrl"
    price_history: List[float] = []
    
    # --- STRATEGY PARAMS (Professional Day Trade Setup) ---
    # Ticks are every 10 seconds. 
    ma_short_period = 30    # 5 minutes (30 * 10s)
    ma_long_period = 120    # 20 minutes (120 * 10s)
    signal_threshold = 0.003 # 0.3% buffer to overcome Foxbit fees (0.5% + 0.1% slippage)
    cooldown_seconds = 1800 # 30 minutes wait after a trade to avoid churn
    
    last_trade_time = 0
    error_counter = 0

    while state.is_running:
        try:
            # Update heartbeat
            if not hasattr(state, "health_metrics"):
                state.health_metrics = {}
            
            state.health_metrics["trading_engine"] = time.time()

            # 1. Use shared state price (updated by market_data_loop)
            if state.last_price == 0 or (time.time() - state.last_update > 20):
                 if state.last_price > 0:
                     logger.warning("Market data stale. Skipping tick.")
                 await asyncio.sleep(1)
                 continue
                
            current_price = state.last_price
            price_history.append(current_price)
            
            if len(price_history) > ma_long_period + 5:
                price_history.pop(0)
            
            # Periodic Heartbeat Log
            if not hasattr(state, "last_heartbeat"): state.last_heartbeat = 0
            if time.time() - state.last_heartbeat > 30:
                state.last_heartbeat = time.time()
                short_ma_val = sum(price_history[-ma_short_period:]) / len(price_history[-ma_short_period:]) if len(price_history) >= ma_short_period else 0
                state.log(f"Robot watching market... Price: R$ {current_price:.2f} | SMA({ma_short_period}): {short_ma_val:.2f}", level="DEBUG")

            # 2. Update Broker
            state.broker.process_data_tick(current_price)
            
            # Update Risk Engine with Equity
            total_equity = state.broker.balance + (state.broker.holdings * current_price)
            state.risk_engine.update_equity(total_equity)

            # 3. Strategy Logic (Smoothed SMA Crossover)
            if len(price_history) >= ma_long_period:
                short_ma = sum(price_history[-ma_short_period:]) / ma_short_period
                long_ma = sum(price_history[-ma_long_period:]) / ma_long_period
                
                # Cooldown check
                in_cooldown = (time.time() - last_trade_time) < cooldown_seconds

                # --- BUY SIGNAL ---
                # Check if short_ma is at least 0.1% above long_ma
                if short_ma > (long_ma * (1 + signal_threshold)) and not in_cooldown:
                    balance = state.broker.balance
                    if balance > 10: # Min balance
                        # Use 98% of balance to maximize compounding (leaving 2% buffer for price fluctuation/fees)
                        quantity_to_buy = (balance * 0.98) / current_price
                        risk_check = state.risk_engine.validate_trade(symbol, "buy", quantity_to_buy, current_price, total_equity)
                        
                        if risk_check["allowed"]:
                            order = Order(
                                id=str(int(time.time()*1000)),
                                symbol=symbol, side="buy", quantity=quantity_to_buy,
                                price=current_price, type="market"
                            )
                            state.broker.place_order(order)
                            last_trade_time = time.time()
                            state.entry_price = current_price # Track entry for TP
                            logger.info(f"SIGNAL BUY @ {current_price} (Strength: {((short_ma/long_ma)-1)*100:.3f}%)")

                # --- PROFIT PROTECTION (TRAILING STOP) ---
                # Calculate approximate entry price (weighted average not stored, assuming last buy price or calculating from Equity)
                # Simplified: Equity = Balance + (Holdings * Price). 
                # Invested = Total Initial - Balance. (Not reliable across sessions)
                # Better: Use Moving Average as dynamic support.
                
                # Logic: If Price is > 2% above Long MA (Overextended) AND drops below Short MA -> SELL
                if current_price > (long_ma * 1.02):
                     if current_price < short_ma:
                         holdings = state.broker.holdings
                         if holdings > 0.00001:
                             # TAKE PROFIT / PROTECTION
                             order = Order(
                                  id=str(int(time.time()*1000)),
                                  symbol=symbol, side="sell", quantity=holdings,
                                  price=current_price, type="market"
                             )
                             state.broker.place_order(order)
                             last_trade_time = time.time()
                             last_trade_time = time.time()
                             state.entry_price = 0.0 # Reset entry
                             logger.info(f"PROTECTION SELL @ {current_price} (Profit Lock - Price crossed ShortMA)")

                # --- FIXED TAKE PROFIT (4%) ---
                if state.broker.holdings > 0.00001 and state.entry_price > 0:
                    profit_pct = (current_price - state.entry_price) / state.entry_price
                    if profit_pct >= 0.04: # 4% target
                        logger.info(f"💰 TAKE PROFIT TRIGGERED! Profit: {profit_pct*100:.2f}% (Target: 4.0%)")
                        order = Order(
                             id=str(int(time.time()*1000)),
                             symbol=symbol, side="sell", quantity=state.broker.holdings,
                             price=current_price, type="market"
                        )
                        state.broker.place_order(order)
                        state.entry_price = 0.0
                        last_trade_time = time.time()


                # --- SELL SIGNAL ---
                # Check if short_ma is at least 0.1% below long_ma
                elif short_ma < (long_ma * (1 - signal_threshold)):
                    holdings = state.broker.holdings
                    if holdings > 0.00001:
                        order = Order(
                             id=str(int(time.time()*1000)),
                             symbol=symbol, side="sell", quantity=holdings,
                             price=current_price, type="market"
                        )
                        state.broker.place_order(order)
                        last_trade_time = time.time()
                        logger.info(f"SIGNAL SELL @ {current_price} (Strength: {((long_ma/short_ma)-1)*100:.3f}%)")
            
            error_counter = 0

        except Exception as e:
            error_counter += 1
            state.log(f"Trading Loop Error ({error_counter}/3): {e}", level="ERROR")
            if error_counter >= 3:
                state.is_running = False
                state.fatal_error = f"AUTO-STOP: {str(e)}"
                break

        # CRITICAL: Yield control to event loop
        await asyncio.sleep(1)

    state.log("Trading loop stopped.")

# Serve Frontend (Optional, if we build it)
# from fastapi.staticfiles import StaticFiles
# app.mount("/", StaticFiles(directory="../frontend/dist", html=True), name="static")
