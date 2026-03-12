from data_handler import fetch_data
from strategy import generate_signals
from analytics import calculate_returns

def run_backtest(ticker: str, start_date: str, end_date: str):
    print(f"\n========== STARTING SYSTEMATIC BACKTEST ==========")
    print(f"Target Asset: {ticker} | Period: {start_date} to {end_date}")
    
    # 1. Ingest Data
    df = fetch_data(ticker, start_date, end_date)
    
    # 2. Generate Alpha Signals
    df = generate_signals(df, window=20, z_threshold=2.0)
    
    # 3. Calculate Market Returns
    df = calculate_returns(df)
    
    # 4. Calculate Strategy Returns (The Shift is CRITICAL)
    # We shift the signal down by 1 row to prevent lookahead bias.
    df['Strategy_Return'] = df['Signal'].shift(1) * df['Daily_Return']
    
    # Drop the NaN created by the shift
    df.dropna(inplace=True)
    
    # 5. Evaluate Performance (Cumulative compounding)
    # Formula: Product of (1 + return) - 1
    market_cumulative_return = (df['Daily_Return'] + 1).prod() - 1
    strategy_cumulative_return = (df['Strategy_Return'] + 1).prod() - 1
    
    # Calculate Sharpe Ratios
    market_sharpe = (df['Daily_Return'].mean() * 252) / (df['Daily_Return'].std() * (252**0.5))
    strat_sharpe = (df['Strategy_Return'].mean() * 252) / (df['Strategy_Return'].std() * (252**0.5))
    
    print("\n========== BACKTEST RESULTS ==========")
    print(f"Market Return (Buy & Hold): {market_cumulative_return:.2%}")
    print(f"Strategy Cumulative Return: {strategy_cumulative_return:.2%}")
    print(f"Market Sharpe Ratio:        {market_sharpe:.2f}")
    print(f"Strategy Sharpe Ratio:      {strat_sharpe:.2f}")
    print("==================================================\n")

if __name__ == "__main__":
    # Let's run the full simulation on the S&P 500 for the last 4 years
    run_backtest("SPY", "2020-01-01", "2024-01-01")