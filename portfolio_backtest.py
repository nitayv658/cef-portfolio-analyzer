

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import yfinance as yf
from datetime import datetime, timedelta
import warnings

warnings.filterwarnings("ignore", category=FutureWarning)

# ---------------- CONFIG ----------------
TICKERS_WDI = ["PDI", "BIT", "DSL", "KIO", "EVV", "WDI"]
TICKERS_GOF = ["PDI", "BIT", "DSL", "KIO", "EVV", "GOF"]
WEIGHTS = np.array([0.25, 0.15, 0.15, 0.15, 0.15, 0.15])

# Validate weights sum to 1.0
if not np.isclose(WEIGHTS.sum(), 1.0):
    raise ValueError(f"Weights must sum to 1.0, currently sum to {WEIGHTS.sum():.4f}")

START = (datetime.today() - timedelta(days=365 * 5)).strftime("%Y-%m-%d")
END = datetime.today().strftime("%Y-%m-%d")
REBALANCE = "monthly"  # options: 'none', 'monthly'
# ----------------------------------------


def show_bid_ask(tickers):
    """Display current bid and ask prices for each ticker."""
    print("\n" + "="*80)
    print("CURRENT MARKET DATA")
    print("="*80)
    print(f"{'Ticker':<8} {'Last':<10} {'Bid':<10} {'Ask':<10} {'Spread':<10} {'Div Yield':<12} {'Volume':<12}")
    print("-"*80)
    
    for ticker in tickers:
        try:
            t = yf.Ticker(ticker)
            info = t.info
            
            # Get most reliable current price
            current_price = (info.get('currentPrice') or 
                           info.get('regularMarketPrice') or 
                           info.get('previousClose') or
                           info.get('navPrice'))
            
            bid = info.get('bid', 0)
            ask = info.get('ask', 0)
            div_yield = info.get('dividendYield', 0) or info.get('trailingAnnualDividendYield', 0)
            volume = info.get('volume') or info.get('regularMarketVolume')
            
            # Format output
            price_str = f"${current_price:.2f}" if current_price else "N/A"
            bid_str = f"${bid:.2f}" if bid and bid > 0 else "N/A"
            ask_str = f"${ask:.2f}" if ask and ask > 0 else "N/A"
            
            if bid and ask and bid > 0 and ask > 0:
                spread = ask - bid
                spread_str = f"${spread:.2f}"
                spread_pct = f"({spread/bid*100:.2f}%)"
            else:
                spread_str = "N/A"
                spread_pct = ""
            
            div_str = f"{div_yield*100:.2f}%" if div_yield else "N/A"
            vol_str = f"{volume:,}" if volume else "N/A"
            
            print(f"{ticker:<8} {price_str:<10} {bid_str:<10} {ask_str:<10} {spread_str:<10} {div_str:<12} {vol_str:<12}")
            
        except Exception as e:
            print(f"{ticker:<8} ⚠️ Error: {str(e)[:60]}")
    
    print("="*80)
    print("Note: Bid/Ask may show 'N/A' when markets are closed or for certain securities")
    print("="*80 + "\n")


def get_prices(tickers, max_retries=3):
    """Download historical adjusted close prices for each ticker."""
    all_data = pd.DataFrame()

    for t in tickers:
        for attempt in range(max_retries):
            try:
                d = yf.download(t, start=START, end=END, progress=False, auto_adjust=False)
                if "Adj Close" in d.columns:
                    d = d[["Adj Close"]].rename(columns={"Adj Close": t})
                    all_data = pd.concat([all_data, d], axis=1)
                    print(f"✅ Downloaded {t}")
                    break
                else:
                    raise ValueError("No 'Adj Close' in data")
            except Exception as e:
                print(f"⚠️  Failed {t} (attempt {attempt + 1}/{max_retries}): {e}")
        else:
            print(f"❌ Could not download {t} after {max_retries} attempts.")

    all_data = all_data.dropna(how="all")
    return all_data


def compute_portfolio(prices, weights, rebalance="none"):
    """Compute portfolio value over time (buy-and-hold or monthly rebalance)."""
    weights = np.array(weights)
    weights = weights / weights.sum()
    prices = prices.dropna()

    if len(prices.columns) != len(weights):
        valid_cols = prices.columns.tolist()
        print(f"⚠️ Warning: missing tickers, adjusting weights to {valid_cols}")
        weights = weights[: len(valid_cols)]
        weights = weights / weights.sum()

    if rebalance == "none":
        portfolio = (prices / prices.iloc[0]) @ weights
    else:
        portfolio_value = 1.0
        shares = (weights * portfolio_value) / prices.iloc[0]
        port_series = pd.Series(index=prices.index, dtype=float)
        current_month = prices.index[0].to_period("M")

        for date in prices.index:
            if date.to_period("M") != current_month:
                current_month = date.to_period("M")
                portfolio_value = (prices.loc[date] * shares).sum()
                shares = (weights * portfolio_value) / prices.loc[date]
            port_series.loc[date] = (prices.loc[date] * shares).sum()

        portfolio = port_series / port_series.iloc[0]

    return portfolio


def summarize_and_plot(portfolio, name="Portfolio"):
    """Print summary stats and save cumulative chart."""
    cum_ret = portfolio / portfolio.iloc[0] - 1
    total_return = cum_ret.iloc[-1]
    daily_rets = portfolio.pct_change().dropna()

    # Calculate annualized return using actual calendar days
    num_days = (portfolio.index[-1] - portfolio.index[0]).days
    num_years = num_days / 365.25
    annualized_return = (1 + total_return) ** (1 / num_years) - 1 if num_years > 0 else 0

    annualized_vol = daily_rets.std() * np.sqrt(252)
    running_max = portfolio.cummax()
    drawdowns = (portfolio - running_max) / running_max
    max_dd = drawdowns.min()

    print(f"\n=== {name} Summary ===")
    print(f"Period: {portfolio.index[0].date()} to {portfolio.index[-1].date()}")
    print(f"Total return: {total_return:.2%}")
    print(f"Annualized return: {annualized_return:.2%}")
    print(f"Annualized vol: {annualized_vol:.2%}")
    print(f"Max drawdown: {max_dd:.2%}")

    plt.figure(figsize=(10, 5))
    plt.plot(portfolio.index, portfolio / portfolio.iloc[0], label=name)
    plt.title(f"{name} — Cumulative Performance (5Y)")
    plt.xlabel("Date")
    plt.ylabel("Cumulative return (normalized to 1)")
    plt.grid(True)
    plt.legend()
    plt.tight_layout()
    plt.savefig(f"{name.replace(' ', '_')}_chart.png")
    plt.show()
    print(f"📊 Chart saved: {name.replace(' ', '_')}_chart.png")

    out = pd.DataFrame({"portfolio": portfolio})
    out.to_csv(f"{name.replace(' ', '_')}_data.csv")
    print(f"💾 CSV saved: {name.replace(' ', '_')}_data.csv")


def run_variant(tickers, weights, variant_name):
    print(f"\n🔹 Running variant: {variant_name}")
    prices = get_prices(tickers)
    if prices.empty:
        print("❌ No data downloaded. Skipping.")
        return
    portfolio = compute_portfolio(prices, weights, rebalance=REBALANCE)
    summarize_and_plot(portfolio, name=variant_name)


# ---------------- RUN ----------------
if __name__ == "__main__":
    # Show current bid/ask prices for both portfolios
    print("\n🔹 WDI PORTFOLIO - Current Bid/Ask Prices")
    show_bid_ask(TICKERS_WDI)
    
    print("\n🔹 GOF PORTFOLIO - Current Bid/Ask Prices")
    show_bid_ask(TICKERS_GOF)
    
    # Run backtests
    run_variant(TICKERS_WDI, WEIGHTS, "Custom_ETF_WDI_variant")
    run_variant(TICKERS_GOF, WEIGHTS, "Custom_ETF_GOF_variant")
