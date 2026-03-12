import yfinance as yf
import pandas as pd

def fetch_data(ticker: str, start_date: str, end_date: str) -> pd.DataFrame:
    """
    Downloads and cleans historical market data for a given ticker.
    Dynamically handles yfinance API version changes to ensure structural integrity.
    """
    print(f"[*] Fetching data for {ticker} from {start_date} to {end_date}...")
    
    # We explicitly tell yfinance NOT to auto-adjust, forcing it to give us raw Close and Adj Close
    df = yf.download(ticker, start=start_date, end=end_date, progress=False, auto_adjust=False)
    
    if df.empty:
        raise ValueError(f"No data found for {ticker}. Check the ticker symbol or dates.")

    # yfinance sometimes returns a MultiIndex (e.g., Level 0: 'Close', Level 1: 'SPY')
    # This list comprehension safely extracts just the price labels, discarding the ticker label.
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = [col[0] for col in df.columns]

    # Failsafe: If the API STILL refuses to give us 'Adj Close' (due to a forced version update),
    # we mathematically assume 'Close' is already adjusted and duplicate it to maintain our pipeline.
    if 'Adj Close' not in df.columns and 'Close' in df.columns:
        print("[*] Warning: API omitted 'Adj Close'. Assuming 'Close' is already adjusted.")
        df['Adj Close'] = df['Close']

    # Enforce our strict mathematical structure
    df = df[['Open', 'High', 'Low', 'Close', 'Adj Close', 'Volume']]
    
    df.dropna(inplace=True)
    
    print(f"[*] Successfully loaded {len(df)} trading days.")
    return df

# --- TESTING BLOCK ---
if __name__ == "__main__":
    try:
        test_df = fetch_data("SPY", "2020-01-01", "2024-01-01")
        print("\nFirst 5 rows of clean data:")
        print(test_df.head())
    except Exception as e:
        print(f"Pipeline Error: {e}")