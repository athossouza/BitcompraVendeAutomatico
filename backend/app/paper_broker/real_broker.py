
import logging
import os
from datetime import datetime
from ..foxbit_client.binance_client import BinanceClient
from ..storage import models, database
from .broker import Order

logger = logging.getLogger(__name__)

class RealBroker:
    """
    Real execution broker delegating to Binance.
    Replaces PaperBroker when TRADING_MODE=LIVE.
    """
    def __init__(self):
        self.api_key = os.getenv("BINANCE_API_KEY")
        self.api_secret = os.getenv("BINANCE_SECRET_KEY")
        
        if not self.api_key or not self.api_secret:
             logger.critical("❌ MISSING BINANCE CREDENTIALS! Check .env")
             raise ValueError("Missing Binance Credentials")
             
        self.client = BinanceClient(self.api_key, self.api_secret)
        self.balance = 0.0 # BRL
        self.holdings = 0.0 # BTC
        self.orders = []
        
        # Initial Balance Sync
        self.sync_balances()
        self.sync_history() # Sync past trades
        self.last_sync = 0 # Initialize sync timer
        logger.info(f"🔌 Connected to Binance. Balance: R${self.balance:.2f} | BTC: {self.holdings}")

    def sync_balances(self):
        try:
            self.balance = self.client.get_asset_balance("BRL")
            self.holdings = self.client.get_asset_balance("BTC")
        except Exception as e:
            logger.error(f"Failed to sync balances: {e}")

    def sync_history(self):
        """
        Fetch historical trades from Binance and populate DB if missing.
        """
        try:
            logger.info("🔄 Syncing Trade History from Binance...")
            binance_trades = self.client.get_my_trades("BTCBRL", limit=20)
            
            db = database.SessionLocal()
            count = 0
            
            for t in binance_trades:
                # Binance keys: id, orderId, price, qty, commission, time, isBuyer
                trade_id = int(t['orderId']) # Using OrderID as Trade ID for 1-to-1 mapping
                
                exists = db.query(models.Trade).filter(models.Trade.id == trade_id).first()
                if not exists:
                    side = "buy" if t['isBuyer'] else "sell"
                    price = float(t['price'])
                    qty = float(t['qty'])
                    dt = datetime.fromtimestamp(t['time'] / 1000)
                    
                    new_trade = models.Trade(
                        id=trade_id,
                        symbol="BTCBRL",
                        side=side,
                        quantity=qty,
                        # price=price, <-- REMOVED (Invalid)
                        status="filled",
                        entered_at=dt,
                        entry_price=price if side == "buy" else price, # Store effective price
                        exit_price=price if side == "sell" else None
                    )
                    db.add(new_trade)
                    count += 1
            
            if count > 0:
                db.commit()
                logger.info(f"✅ Synced {count} new trades from Binance to DB.")
            else:
                logger.info("✅ Trade History is up to date.")
                
            db.close()
            
        except Exception as e:
            logger.error(f"Failed to sync history: {e}")

    @property
    def trade_history(self):
        """
        Fetch trade history from DB and format as Orders for Frontend consistency.
        Matches logic in PaperBroker._load_state.
        """
        try:
            db = database.SessionLocal()
            trades = db.query(models.Trade).order_by(models.Trade.entered_at.desc()).limit(50).all()
            db.close()
            
            # Transform DB Trade -> API Order format
            formatted_history = []
            for t in trades:
                # Use entry_price as the filled_price representation
                price = t.entry_price if t.entry_price is not None else 0.0
                
                # Create dict that mimics Order object attributes expected by frontend
                o = {
                    "id": str(t.id),
                    "symbol": t.symbol,
                    "side": t.side,
                    "type": "market",
                    "quantity": t.quantity,
                    "price": price,
                    "status": t.status,
                    "created_at": t.entered_at,
                    "filled_at": t.entered_at, # Frontend uses this for date formatting
                    "filled_price": price      # Frontend uses this for display
                }
                formatted_history.append(o)
                
            return formatted_history
            
        except Exception as e:
            logger.error(f"Failed to fetch trade history: {e}")
            return []

    def place_order(self, order: Order) -> Order:
        """
        Execute Real Order on Binance and persist to DB.
        """
    def place_order(self, order: Order) -> Order:
        """
        Execute Real Order on Binance and persist to DB.
        """
        try:
            logger.info(f"🚨 EXECUTING REAL ORDER: {order.side.upper()} {order.quantity} BTC")
            
            # 1. Fetch Symbol Info (Step Size)
            symbol_info = self.client.get_symbol_info("BTCBRL")
            step_size = 0.00001 # Default fallback
            for f in symbol_info.get("filters", []):
                if f["filterType"] == "LOT_SIZE":
                    step_size = float(f.get("stepSize", 0.00001))
            
            target_qty = order.quantity

            # 2. Smart SELL Logic: Handle "Sell All" & Fees
            if order.side.upper() == "SELL":
                 # Sync latest balance to know exactly what we have (after purchase fees)
                 self.sync_balances() # Updates self.holdings
                 
                 # If target is very close to holdings (>99%), assume Full Exit.
                 # E.g. Buy 0.00005 -> Get 0.00004995 -> Sell 0.00005 (Fail) -> Adjust to 0.00004995
                 if target_qty >= (self.holdings * 0.99):
                     logger.info(f"🔄 Smart Sell: Adjusting quantity {target_qty} -> {self.holdings} (Max Available)")
                     target_qty = self.holdings
            
            # 3. Normalize Quantity to Step Size
            # Floor execution to nearest step size (e.g. 0.00004995 -> 0.00004)
            # This handles the "Dust" issue automatically.
            import math
            normalized_qty = float(int(target_qty / step_size) * step_size)
            
            # 4. Format for API
            # Avoids scientific notation and uses correct precision based on step size
            import decimal
            # Calculate decimals from step_size (e.g. 0.00001 -> 5 decimals)
            decimals = 0
            if step_size < 1:
                decimals = int(abs(math.log10(step_size)))
            
            qty_str = "{:.{}f}".format(normalized_qty, decimals)

            logger.info(f"📏 Normalized Qty: {qty_str} (Step: {step_size})")

            if float(qty_str) <= 0:
                 logger.warning("⚠️ Trade Quantity is Zero after normalization (Dust?). Skipping.")
                 return order

            response = self.client.create_order(
                symbol="BTCBRL",
                side=order.side,
                quantity=float(qty_str), # Client handles formatting too, but we send float
                type="MARKET"
            )
            
            # Update Order Object with Real Fill Data
            order.status = "filled" if response.get("status") == "FILLED" else "open"
            
            # Calculate Avg Price from Fills
            fills = response.get("fills", [])
            if fills:
                total_qty = sum(float(f['qty']) for f in fills)
                total_cost = sum(float(f['price']) * float(f['qty']) for f in fills)
                order.filled_price = total_cost / total_qty if total_qty > 0 else 0.0
            else:
                 # Fallback if no fills (shouldn't happen on market filled)
                 order.filled_price = float(response.get("cummulativeQuoteQty", 0)) / float(response.get("executedQty", 1))

            order.filled_at = datetime.now()
            
            # Re-sync balances immediately
            self.sync_balances()
            
            # --- PERSISTENCE (Save to Supabase) ---
            try:
                db = database.SessionLocal()
                db_trade = models.Trade(
                    id=order.id,
                    symbol=order.symbol,
                    side=order.side,
                    quantity=order.quantity,
                    price=order.filled_price, # Use filled price
                    status=order.status,
                    entered_at=order.filled_at,
                    entry_price=order.filled_price
                )
                db.add(db_trade)
                db.commit()
                db.close()
                logger.info(f"💾 Real Trade {order.side} Saved to DB.")
            except Exception as e:
                logger.error(f"Failed to save real trade to DB: {e}")
            
            return order
            
        except Exception as e:
            logger.error(f"❌ REAL ORDER FAILED: {e}")
            order.status = "rejected"
            return order

    def cancel_order(self, order_id: str):
        logger.warning("Cancel order not fully implemented for Market Orders (Instant fill)")
        pass

    def process_data_tick(self, current_price: float):
        """
        Called by main loop. RealBroker delegates execution to Binance.
        Periodically sync balance to detect deposits.
        """
        import time
        if time.time() - self.last_sync > 60: # Sync every 60 seconds
             # logger.debug("⏳ Auto-Syncing Balances...") 
             self.sync_balances()
             self.last_sync = time.time()
