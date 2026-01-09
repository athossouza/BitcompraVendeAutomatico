import pytest
from backend.app.paper_broker.broker import PaperBroker, Order

def test_broker_order_placement():
    broker = PaperBroker(initial_balance=10000)
    order = Order(id="1", symbol="BTCBRL", side="buy", type="market", quantity=0.01, price=0)
    broker.place_order(order)
    assert len(broker.orders) == 1
    assert broker.orders[0].status == "open"

def test_broker_market_fill():
    broker = PaperBroker(initial_balance=10000)
    order = Order(id="1", symbol="BTCBRL", side="buy", type="market", quantity=0.1, price=0)
    broker.place_order(order)
    
    # Process tick at 50000. Cost = 5000 + fee
    broker.process_data_tick(50000)
    
    assert order.status == "filled"
    assert broker.holdings == 0.1
    assert broker.balance < 5000 # Paid ~5000 + fees

def test_broker_limit_fill():
    broker = PaperBroker(initial_balance=10000)
    # Buy Limit @ 40000
    order = Order(id="2", symbol="BTCBRL", side="buy", type="limit", quantity=0.1, price=40000)
    broker.place_order(order)
    
    # Tick @ 41000 (No fill)
    broker.process_data_tick(41000)
    assert order.status == "open"
    
    # Tick @ 39000 (Fill)
    broker.process_data_tick(39000)
    assert order.status == "filled"
    assert order.filled_price == 40000 # Naive assumption: fills at limit price if gapped
