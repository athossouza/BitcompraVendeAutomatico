from dataclasses import dataclass
from typing import List, Optional
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

@dataclass
class TradeRisk:
    max_position_size_pct: float = 0.80  # 80% of equity (Aggressive for small wallets)
    stop_loss_pct: float = 0.05          # 5% max loss per trade
    max_drawdown_limit: float = 0.30     # 30% global drawdown kill switch

class RiskEngine:
    def __init__(self, config: TradeRisk):
        self.config = config
        self.daily_trades = 0
        self.max_daily_trades = 10
        self.last_trade_time = datetime.min
        self.consecutive_losses = 0
        self.cooldown_until = datetime.min
        self.kill_switch_active = False
        self.initial_balance = 0.0
        self.current_balance = 0.0

    def update_equity(self, total_equity: float):
        """Update current equity (Balance + Holdings Value)"""
        if self.initial_balance == 0:
            self.initial_balance = total_equity
        self.current_balance = total_equity # We track equity as 'balance' for drawdown purposes
        self._check_global_drawdown()



    def _check_global_drawdown(self):
        if self.initial_balance <= 0:
            return
        # Drawdown = (Peak - Current) / Peak 
        # For simplicity in V1: (Initial - Current) / Initial
        drawdown = (self.initial_balance - self.current_balance) / self.initial_balance
        
        if drawdown >= self.config.max_drawdown_limit:
            self.kill_switch_active = True
            logger.critical(f"KILL SWITCH ENGAGED: Max drawdown {drawdown*100:.2f}% reached. Equity: {self.current_balance:.2f} (Init: {self.initial_balance:.2f})")

    def can_trade(self) -> bool:
        if self.kill_switch_active:
            logger.warning("Trade rejected: Kill switch is active.")
            return False
        
        if datetime.now() < self.cooldown_until:
            logger.warning("Trade rejected: In cooldown.")
            return False

        if self.daily_trades >= self.max_daily_trades:
            logger.warning("Trade rejected: Daily trade limit reached.")
            return False
            
        return True

    def register_trade_result(self, pnl: float):
        self.daily_trades += 1
        if pnl < 0:
            self.consecutive_losses += 1
        else:
            self.consecutive_losses = 0
        
        # Cooldown logic: 3 losses in a row -> 1 hour cooldown
        if self.consecutive_losses >= 3:
            self.cooldown_until = datetime.now() + timedelta(hours=1)
            logger.info("3 Consecutive losses. Cooldown activated for 1 hour.")
            self.consecutive_losses = 0

    def validate_trade(self, symbol: str, side: str, quantity: float, price: float, equity: float) -> dict:
        """
        Check if a trade is allowed based on risk parameters.
        Returns: {"allowed": bool, "reason": str}
        """
        if not self.can_trade():
             return {"allowed": False, "reason": "Risk Engine blocked (Kill switch, cooldown, etc)"}

        # Check position size (Value of trade vs Equity)
        trade_value = price * quantity
        if trade_value > (equity * self.config.max_position_size_pct):
            reason = f"Position size {trade_value:.2f} > {self.config.max_position_size_pct*100}% of equity {equity:.2f}"
            logger.warning(f"Trade rejected: {reason}")
            return {"allowed": False, "reason": reason}
        
        # Stop Loss check is tricky without a specific stop price in the order. 
        # For V1, we skip explicit stop_loss check here or assuming a default tight stop.
        # We could implement a check if we passed a stop_price arg.
        
        return {"allowed": True, "reason": "OK"}
