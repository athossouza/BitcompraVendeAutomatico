import sqlite3
import os

def migrate():
    conn = sqlite3.connect('storage.db')
    cursor = conn.cursor()
    
    # Get trades
    cursor.execute("SELECT symbol, side, entry_price, exit_price, quantity, pnl, status, entered_at, exited_at, strategy_name FROM trades")
    trades = cursor.fetchall()
    
    # Get configurations
    cursor.execute("SELECT key, value FROM configurations")
    configs = cursor.fetchall()
    
    with open('migration.sql', 'w') as f:
        f.write("-- Migration Script\n\n")
        f.write("CREATE TABLE IF NOT EXISTS public.trades (\n")
        f.write("    id SERIAL PRIMARY KEY,\n")
        f.write("    symbol VARCHAR,\n")
        f.write("    side VARCHAR,\n")
        f.write("    entry_price FLOAT,\n")
        f.write("    exit_price FLOAT,\n")
        f.write("    quantity FLOAT,\n")
        f.write("    pnl FLOAT,\n")
        f.write("    status VARCHAR,\n")
        f.write("    entered_at TIMESTAMP WITH TIME ZONE,\n")
        f.write("    exited_at TIMESTAMP WITH TIME ZONE,\n")
        f.write("    strategy_name VARCHAR\n")
        f.write(");\n\n")
        
        f.write("CREATE TABLE IF NOT EXISTS public.configurations (\n")
        f.write("    key VARCHAR PRIMARY KEY,\n")
        f.write("    value VARCHAR\n")
        f.write(");\n\n")
        
        f.write("DELETE FROM public.trades;\n")
        for t in trades:
            vals = []
            for v in t:
                if v is None: vals.append("NULL")
                elif isinstance(v, str): vals.append(f"'{v}'")
                else: vals.append(str(v))
            f.write(f"INSERT INTO public.trades (symbol, side, entry_price, exit_price, quantity, pnl, status, entered_at, exited_at, strategy_name) VALUES ({', '.join(vals)});\n")
            
        f.write("\nDELETE FROM public.configurations;\n")
        for c in configs:
            f.write(f"INSERT INTO public.configurations (key, value) VALUES ('{c[0]}', '{c[1]}');\n")
            
    print("Migration SQL generated in migration.sql")
    conn.close()

if __name__ == '__main__':
    migrate()
