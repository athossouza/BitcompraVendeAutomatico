import pytest
from backend.app.risk_engine.engine import RiskEngine, TradeRisk

def test_risk_initialization():
    config = TradeRisk()
    engine = RiskEngine(config)
    engine.set_balance(10000)
    assert engine.current_balance == 10000
    assert engine.kill_switch_active == False

def test_drawdown_kill_switch():
    config = TradeRisk(max_drawdown_limit=0.10)
    engine = RiskEngine(config)
    engine.set_balance(10000)
    
    # Loss of 11%
    engine.set_balance(8900) 
    assert engine.kill_switch_active == True
    assert engine.can_trade() == False

def test_consecutive_loss_cooldown():
    engine = RiskEngine(TradeRisk())
    engine.register_trade_result(-100)
    engine.register_trade_result(-100)
    assert engine.consecutive_losses == 2
    engine.register_trade_result(-100)
    assert engine.consecutive_losses == 0 # Resets after triggering cooldown
    assert engine.can_trade() == False # In cooldown
