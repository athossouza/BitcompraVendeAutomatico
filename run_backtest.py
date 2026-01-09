from datetime import datetime
from backend.app.core.bot import BotEngine

if __name__ == "__main__":
    print("Running Backtest...")
    engine = BotEngine()
    
    # Example Parameters
    start = datetime(2023, 1, 1)
    end = datetime(2023, 12, 1)
    
    # Run Strategy A
    print("\n--- Strategy A (Trend) ---")
    engine.run_backtest("StrategyA", "BTC-USD", start, end, 10000.0)
    
    # Run Strategy B
    print("\n--- Strategy B (Breakout) ---")
    engine.run_backtest("StrategyB", "BTC-USD", start, end, 10000.0)
