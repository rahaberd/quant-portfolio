import matplotlib.pyplot as plt
import pandas as pd
import os

def plot_equity_curve(df: pd.DataFrame, ticker: str):
    """
    Generates and saves a professional-grade performance tearsheet.
    Mathematically calculates the compounded growth of $1 invested.
    """
    print("\n[*] Generating performance tearsheet...")
    
    # 1. Calculate Cumulative Growth
    # .cumprod() calculates the compounding effect over time.
    df['Market_Growth'] = (1 + df['Daily_Return']).cumprod()
    df['Strategy_Growth'] = (1 + df['Strategy_Return']).cumprod()
    
    # 2. Set up the professional visual style (Dark Mode Quant aesthetic)
    plt.style.use('dark_background')
    fig, ax = plt.subplots(figsize=(12, 6))
    
    # 3. Plot the data
    # The Market is a dull gray (baseline). The Strategy is a sharp cyan (focus).
    ax.plot(df.index, df['Market_Growth'], color='gray', label=f'{ticker} Buy & Hold', alpha=0.6, linewidth=1.5)
    ax.plot(df.index, df['Strategy_Growth'], color='cyan', label='Z-Score Strategy', linewidth=2.0)
    
    # 4. Formatting the Tearsheet
    ax.set_title(f"Quantitative Backtest: {ticker} Mean Reversion", fontsize=16, fontweight='bold')
    ax.set_ylabel("Cumulative Growth ($1 Invested)", fontsize=12)
    ax.set_xlabel("Date", fontsize=12)
    ax.legend(loc='upper left', fontsize=12)
    ax.grid(True, linestyle='--', alpha=0.3)
    
    # 5. Save the output
    # We create a 'results' folder automatically if it doesn't exist
    os.makedirs("results", exist_ok=True)
    save_path = f"results/{ticker}_tearsheet.png"
    plt.savefig(save_path, dpi=300, bbox_inches='tight')
    
    print(f"[*] Tearsheet saved successfully to: {save_path}")
    
    # Close the plot to free up machine memory (Critical for large loops later)
    plt.close()