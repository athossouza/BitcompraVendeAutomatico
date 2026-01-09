-- Migration Script

CREATE TABLE IF NOT EXISTS public.trades (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR,
    side VARCHAR,
    entry_price FLOAT,
    exit_price FLOAT,
    quantity FLOAT,
    pnl FLOAT,
    status VARCHAR,
    entered_at TIMESTAMP WITH TIME ZONE,
    exited_at TIMESTAMP WITH TIME ZONE,
    strategy_name VARCHAR
);

CREATE TABLE IF NOT EXISTS public.configurations (
    key VARCHAR PRIMARY KEY,
    value VARCHAR
);

DELETE FROM public.trades;
INSERT INTO public.trades (symbol, side, entry_price, exit_price, quantity, pnl, status, entered_at, exited_at, strategy_name) VALUES ('btcbrl', 'buy', 489064.57599999994, NULL, 0.00019648938957296305, 0.0, 'filled', '2025-12-18 13:30:49.896027', NULL, 'SMA_Crossover');
INSERT INTO public.trades (symbol, side, entry_price, exit_price, quantity, pnl, status, entered_at, exited_at, strategy_name) VALUES ('btcbrl', 'buy', 489729.23999999993, NULL, 0.00019622271277900416, 0.0, 'filled', '2025-12-18 13:30:50.534290', NULL, 'SMA_Crossover');
INSERT INTO public.trades (symbol, side, entry_price, exit_price, quantity, pnl, status, entered_at, exited_at, strategy_name) VALUES ('btcbrl', 'sell', 488186.325, NULL, 0.00019648938957296305, 0.0, 'filled', '2025-12-18 14:12:39.255143', NULL, 'SMA_Crossover');
INSERT INTO public.trades (symbol, side, entry_price, exit_price, quantity, pnl, status, entered_at, exited_at, strategy_name) VALUES ('btcbrl', 'sell', 487663.848, NULL, 0.00019622271277900416, 0.0, 'filled', '2025-12-18 14:12:44.310065', NULL, 'SMA_Crossover');

DELETE FROM public.configurations;
INSERT INTO public.configurations (key, value) VALUES ('balance', '118.63578956291393');
INSERT INTO public.configurations (key, value) VALUES ('holdings', '0.0');
