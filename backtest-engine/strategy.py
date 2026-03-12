import pandas as pd

def generate_signals(df: pd.DataFrame, window: int = 20, z_threshold: float = 2.0) -> pd.DataFrame:
    """
    Generates Buy/Sell signals using a Z-Score Mean Reversion strategy.
    If price is mathematically 'oversold' (Z < -2), we Buy (1).
    If price is mathematically 'overbought' (Z > 2), we Sell (-1).
    """
    # Always operate on a copy to avoid mutating the original data prematurely
    df = df.copy()

    # 1. Calculate the Simple Moving Average (The "Mean")
    df['SMA'] = df['Adj Close'].rolling(window=window).mean()

    # 2. Calculate the Rolling Standard Deviation (The "Volatility")
    df['Rolling_Std'] = df['Adj Close'].rolling(window=window).std()

    # 3. Calculate the Z-Score 
    # Formula: (Current Price - Mean) / Standard Deviation
    df['Z_Score'] = (df['Adj Close'] - df['SMA']) / df['Rolling_Std']

    # 4. Initialize the Signal column with 0 (Cash/Neutral position)
    df['Signal'] = 0

    # 5. Vectorized Signal Generation
    # We use .loc to instantly assign 1 or -1 across the entire dataframe without loops
    df.loc[df['Z_Score'] < -z_threshold, 'Signal'] = 1   # Price is unnaturally low -> Buy
    df.loc[df['Z_Score'] > z_threshold, 'Signal'] = -1   # Price is unnaturally high -> Sell

    return df

# --- TESTING BLOCK ---
if __name__ == "__main__":
    from data_handler import fetch_data
    
    print("[*] Testing Strategy Module...")
    try:
        raw_data = fetch_data("SPY", "2023-01-01", "2024-01-01")
        strategy_data = generate_signals(raw_data)
        
        # Let's see how many days the strategy actually found a trading signal
        buy_signals = len(strategy_data[strategy_data['Signal'] == 1])
        sell_signals = len(strategy_data[strategy_data['Signal'] == -1])
        
        print(f"\n[*] Strategy execution complete.")
        print(f"[*] Found {buy_signals} Buy signals and {sell_signals} Sell signals in 2023.")
        print("\n[*] Snapshot of a Buy Signal day (if any exist):")
        
        if buy_signals > 0:
            print(strategy_data[strategy_data['Signal'] == 1][['Adj Close', 'SMA', 'Z_Score', 'Signal']].head())
            
    except Exception as e:
        print(f"Strategy Error: {e}")