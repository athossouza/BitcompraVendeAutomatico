import logging
from dataclasses import dataclass
from datetime import datetime

logger = logging.getLogger(__name__)

@dataclass
class Order:
    id: str
    symbol: str
    side: str  # 'buy' or 'sell'
    type: str  # 'market' or 'limit'
    quantity: float
    price: float  # Limit price, or 0 for market
    status: str = "open"  # open, filled, canceled
    created_at: datetime = datetime.now()
    filled_at: datetime = None
    filled_price: float = 0.0

class PaperBroker:
    """
    Simulates a broker execution engine.
    Match orders against real-time market data (ticker/book).
    """
    def __init__(self, initial_balance: float = 10000.0, fee_pct: float = 0.005, slippage_pct: float = 0.001):
        self.balance = initial_balance  # BRL
        self.holdings = 0.0             # BTC
        self.orders = []
        self.fee_pct = fee_pct
        self.slippage_pct = slippage_pct
        self.trade_history = []
        
        # Late import to avoid circular dep if any, though direct import is fine usually
        from ..storage.database import SessionLocal
        from ..storage import models
        self.SessionLocal = SessionLocal
        self.models = models
        
        # Try to restore state
        self._load_state()

    def _load_state(self):
        session = self.SessionLocal()
        try:
            # 1. Load Balance & Holdings
            bal_cfg = session.query(self.models.Configuration).filter_by(key="balance").first()
            hold_cfg = session.query(self.models.Configuration).filter_by(key="holdings").first()
            
            if bal_cfg:
                self.balance = float(bal_cfg.value)
            if hold_cfg:
                self.holdings = float(hold_cfg.value)
                
            # 2. Load Trade History
            # We map DB Trade model back to Order object approx for UI consistency
            db_trades = session.query(self.models.Trade).order_by(self.models.Trade.entered_at.asc()).limit(50).all()
            for t in db_trades:
                # Reconstruct Order object for history display
                o = Order(
                    id=str(t.id),
                    symbol=t.symbol,
                    side=t.side,
                    type="market", # Assuming market for history
                    quantity=t.quantity,
                    price=t.entry_price,
                    status="filled",
                    created_at=t.entered_at,
                    filled_at=t.entered_at,
                    filled_price=t.entry_price
                )
                self.trade_history.append(o)
            
        except Exception as e:
            logger.error(f"Failed to load broker state: {e}")
        finally:
            session.close()

    def _save_state(self):
        session = self.SessionLocal()
        try:
            # Upsert Balance
            bal = session.query(self.models.Configuration).filter_by(key="balance").first()
            if not bal:
                bal = self.models.Configuration(key="balance", value=str(self.balance))
                session.add(bal)
            else:
                bal.value = str(self.balance)

            # Upsert Holdings
            hold = session.query(self.models.Configuration).filter_by(key="holdings").first()
            if not hold:
                hold = self.models.Configuration(key="holdings", value=str(self.holdings))
                session.add(hold)
            else:
                hold.value = str(self.holdings)
            
            session.commit()
        except Exception as e:
            logger.error(f"Failed to save state: {e}")
            session.rollback()
        finally:
            session.close()

    def _persist_trade(self, order: Order):
        session = self.SessionLocal()
        try:
            trade = self.models.Trade(
                symbol=order.symbol,
                side=order.side,
                entry_price=order.filled_price,
                quantity=order.quantity,
                status="filled",
                entered_at=datetime.utcnow(),
                strategy_name="SMA_Crossover" # Default for now
            )
            session.add(trade)
            session.commit()
        except Exception as e:
            logger.error(f"Failed to persist trade: {e}")
            session.rollback()
        finally:
            session.close()

    def place_order(self, order: Order) -> Order:
        logger.info(f"PaperBroker: Placing {order.side} order for {order.quantity} @ {order.type}")
        self.orders.append(order)
        return order

    def cancel_order(self, order_id: str):
        for o in self.orders:
            if o.id == order_id and o.status == "open":
                o.status = "canceled"
                logger.info(f"Order {order_id} canceled.")

    def process_data_tick(self, current_price: float):
        """
        Check open orders against current price.
        Simple simulation:
        - Market orders fill immediately at current_price (+/- slippage)
        - Limit orders fill if price crosses limit.
        """
        for order in self.orders:
            if order.status != "open":
                continue
            
            should_fill = False
            fill_price = current_price

            if order.type == "market":
                should_fill = True
                # Apply slippage
                if order.side == "buy":
                    fill_price = current_price * (1 + self.slippage_pct)
                else:
                    fill_price = current_price * (1 - self.slippage_pct)
            
            elif order.type == "limit":
                if order.side == "buy" and current_price <= order.price:
                    should_fill = True
                    fill_price = order.price # Naively fill at limit
                elif order.side == "sell" and current_price >= order.price:
                    should_fill = True
                    fill_price = order.price

            if should_fill:
                self._execute_fill(order, fill_price)

    def _execute_fill(self, order: Order, price: float):
        cost = price * order.quantity
        fee = cost * self.fee_pct

        if order.side == "buy":
            if self.balance >= (cost + fee):
                self.balance -= (cost + fee)
                self.holdings += order.quantity
                order.status = "filled"
                order.filled_price = price
                order.filled_at = datetime.now()
                self.trade_history.append(order)
                logger.info(f" FILLED BUY: {order.quantity} @ {price:.2f}")

                # Persist
                self._save_state()
                self._persist_trade(order)
            else:
                logger.warning("Insufficient funds for paper trade.")
                order.status = "rejected"

        elif order.side == "sell":
            if self.holdings >= order.quantity:
                self.balance += (cost - fee)
                self.holdings -= order.quantity
                order.status = "filled"
                order.filled_price = price
                order.filled_at = datetime.now()
                self.trade_history.append(order)
                logger.info(f" FILLED SELL: {order.quantity} @ {price:.2f}")
                
                # Persist
                self._save_state()
                self._persist_trade(order)
            else:
                logger.warning("Insufficient holdings for paper trade.")
                order.status = "rejected"
