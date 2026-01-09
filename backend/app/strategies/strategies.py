import backtrader as bt
import logging

class StrategyA_TrendFollowing(bt.Strategy):
    """
    Estratégia A: Tendência (Médias Móveis)
    - Compra: SMA curta cruza acima da SMA longa
    - Venda: SMA curta cruza abaixo da SMA longa
    - Filtro: Volatilidade (Opcional - simples implementação aqui)
    """
    params = (
        ('fast_period', 10),
        ('slow_period', 30),
        ('risk_pct', 0.02),
    )

    def log(self, txt, dt=None):
        dt = dt or self.datas[0].datetime.datetime(0)
        logging.info(f'{dt.isoformat()} {txt}')

    def __init__(self):
        self.sma_fast = bt.indicators.SimpleMovingAverage(
            self.datas[0], period=self.params.fast_period)
        self.sma_slow = bt.indicators.SimpleMovingAverage(
            self.datas[0], period=self.params.slow_period)
        self.crossover = bt.indicators.CrossOver(self.sma_fast, self.sma_slow)

    def next(self):
        if self.position:
            if self.crossover < 0:
                self.log(f'SELL CREATE {self.data.close[0]:.2f}')
                self.close()
        else:
            if self.crossover > 0:
                self.log(f'BUY CREATE {self.data.close[0]:.2f}')
                # Calculate size based on risk would go here
                self.buy()

class StrategyB_Breakout(bt.Strategy):
    """
    Estratégia B: Breakout com ATR Stop
    - Compra: Preço fecha acima da máxima dos últimos N períodos
    - Stop: ATR * k
    """
    params = (
        ('lookback', 20),
        ('atr_period', 14),
        ('atr_multiplier', 2.0),
    )

    def __init__(self):
        self.highest = bt.indicators.Highest(self.data.high, period=self.params.lookback)
        self.atr = bt.indicators.ATR(self.data, period=self.params.atr_period)

    def next(self):
        if not self.position:
            if self.data.close[0] > self.highest[-1]: # Breakout
                self.buy()
        else:
            # Trailing stop logic or simple stop
            stop_price = self.data.close[0] - (self.atr[0] * self.params.atr_multiplier)
            if self.data.close[0] < stop_price:
                 self.close()
