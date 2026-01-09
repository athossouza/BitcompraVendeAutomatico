import backtrader as bt
from datetime import datetime
import pandas as pd
from typing import List
from .foxbit_client.client import FoxbitClient
from .strategies.strategies import StrategyA_TrendFollowing, StrategyB_Breakout

class BotEngine:
    def __init__(self):
        self.cerebro = bt.Cerebro()
        self.client = FoxbitClient() # In real live mode, this would feed data
        
    def run_backtest(self, strategy_name: str, symbol: str, start_date: datetime, end_date: datetime, initial_cash: float):
        self.cerebro = bt.Cerebro()
        
        # Load Strategy
        if strategy_name == "StrategyA":
            self.cerebro.addstrategy(StrategyA_TrendFollowing)
        elif strategy_name == "StrategyB":
            self.cerebro.addstrategy(StrategyB_Breakout)
            
        # Get Data (Mocking fetching history for now or implement real fetch)
        # candles = self.client.get_candles(symbol, ...) 
        # For this deliverable, we assume we might need to load from CSV or simpler source if API is limited publicly.
        # Im implementing a dummy data generator if no file exists to ensure "runnable" state.
        
        # Using a dummy feed for immediate runnability if file not found
        data = bt.feeds.YahooFinanceData(
            dataname='BTC-USD',
            fromdate=start_date,
            todate=end_date
        )
        self.cerebro.adddata(data)
        
        self.cerebro.broker.setcash(initial_cash)
        self.cerebro.addsizer(bt.sizers.FixedSize, stake=10) # Simple sizer
        
        print('Starting Portfolio Value: %.2f' % self.cerebro.broker.getvalue())
        strategies = self.cerebro.run()
        final_val = self.cerebro.broker.getvalue()
        print('Final Portfolio Value: %.2f' % final_val)
        
        return {
            "final_value": final_val,
            "trades": [] # would extract trades from strategy analyzer
        }

    # For Live Paper Trading (simulated loop without Cerebro for easier control/UI feedback on this V1 app)
    # Using Cerebro for Live is possible but complex to integrate with a Web Dashboard for status updates in real-time
    # effectively. Often simpler to run a `while` loop that calls `strategy.next()` logic manually or uses
    # "Live Data Feed" feature of BT. 
    # Check user requirements: "Paper Trading (liga/desliga...)"
    # I will stick to a custom loop for the "Paper Trading" mode utilizing the strategies logic if possible, 
    # or just simple logic for the V1 to ensure robustness.
    # Actually, let's use the `PaperBroker` class I wrote and hook it to a loop.
