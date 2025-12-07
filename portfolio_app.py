import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import yfinance as yf
from datetime import datetime, timedelta
import streamlit as st
import warnings
import database
import ai_advisor

warnings.filterwarnings("ignore", category=FutureWarning)

# ---------------- CONFIG ----------------
TICKERS_WDI = ["PDI", "BIT", "DSL", "KIO", "EVV", "WDI"]
TICKERS_GOF = ["PDI", "BIT", "DSL", "KIO", "EVV", "GOF"]
WEIGHTS = np.array([0.25, 0.15, 0.15, 0.15, 0.15, 0.15])

# Validate weights sum to 1.0
if not np.isclose(WEIGHTS.sum(), 1.0):
    raise ValueError(f"Weights must sum to 1.0, currently sum to {WEIGHTS.sum():.4f}")
# ----------------------------------------

# Initialize database on startup
database.init_database()

# Page config
st.set_page_config(
    page_title="Portfolio Backtest Dashboard",
    page_icon="📊",
    layout="wide"
)

st.title("📊 Custom ETF Portfolio Backtest Dashboard")
st.markdown(f"**Last Updated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

# Initialize session state for custom portfolio (must be before sidebar)
if 'custom_tickers' not in st.session_state:
    st.session_state.custom_tickers = ["SPY"]
if 'custom_weights' not in st.session_state:
    st.session_state.custom_weights = [100.0]

# Load search history from database
search_history = database.load_history_from_database(limit=100)

# Sidebar for configuration
st.sidebar.header("⚙️ Configuration")
portfolio_mode = st.sidebar.radio("Portfolio Mode", ["Preset Portfolios", "Custom Portfolio Builder"])
years_back = st.sidebar.slider("Years of History", 1, 10, 5)
rebalance_option = st.sidebar.selectbox("Rebalancing", ["monthly", "none"])

# Search History in sidebar
st.sidebar.markdown("---")
st.sidebar.header("📜 Search History")
if search_history:
    st.sidebar.write(f"Total searches: {len(search_history)}")

    col1, col2 = st.sidebar.columns(2)

    with col1:
        if st.button("📥 Export", use_container_width=True, key="export_history"):
            csv_data = database.export_history_to_csv()
            st.download_button(
                label="Download CSV",
                data=csv_data,
                file_name=f"search_history_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv",
                use_container_width=True,
                key="download_csv"
            )

    with col2:
        if st.button("🗑️ Clear", use_container_width=True, key="clear_history"):
            database.clear_database_history()
            st.rerun()

    # Show recent searches
    with st.sidebar.expander("View Recent Searches (Last 10)"):
        for entry in search_history[:10]:
            st.write(f"**{entry['timestamp']}**")
            st.write(f"📁 {entry['portfolio_name']}")
            st.write(f"📊 Tickers: {', '.join(entry['tickers'])}")
            st.write(f"⚙️ {entry['years_back']}Y, {entry['rebalance_option']}")

            # Show metrics if available
            metrics = database.get_portfolio_metrics(entry['id'])
            if metrics:
                st.write(f"📈 Return: {metrics['Annualized Return']}")
                st.write(f"📉 Max DD: {metrics['Max Drawdown']}")

            st.markdown("---")
else:
    st.sidebar.info("No search history yet")

START = (datetime.today() - timedelta(days=365 * years_back)).strftime("%Y-%m-%d")
END = datetime.today().strftime("%Y-%m-%d")


@st.cache_data(ttl=300)  # Cache for 5 minutes
def get_current_prices(tickers):
    """Fetch current market data for tickers."""
    data = []
    for ticker in tickers:
        try:
            t = yf.Ticker(ticker)
            info = t.info
            
            current_price = (info.get('currentPrice') or 
                           info.get('regularMarketPrice') or 
                           info.get('previousClose') or
                           info.get('navPrice'))
            
            bid = info.get('bid', 0)
            ask = info.get('ask', 0)
            div_yield = info.get('dividendYield', 0) or info.get('trailingAnnualDividendYield', 0)
            volume = info.get('volume') or info.get('regularMarketVolume')
            
            spread = (ask - bid) if (bid and ask and bid > 0 and ask > 0) else None
            
            data.append({
                'Ticker': ticker,
                'Last Price': f"${current_price:.2f}" if current_price else "N/A",
                'Bid': f"${bid:.2f}" if bid and bid > 0 else "N/A",
                'Ask': f"${ask:.2f}" if ask and ask > 0 else "N/A",
                'Spread': f"${spread:.2f}" if spread else "N/A",
                'Div Yield': f"{div_yield*100:.2f}%" if div_yield else "N/A",
                'Volume': f"{volume:,}" if volume else "N/A"
            })
        except Exception:
            data.append({
                'Ticker': ticker,
                'Last Price': 'Error',
                'Bid': 'N/A',
                'Ask': 'N/A',
                'Spread': 'N/A',
                'Div Yield': 'N/A',
                'Volume': 'N/A'
            })
    
    return pd.DataFrame(data)


@st.cache_data(ttl=3600)  # Cache for 1 hour
def get_historical_prices(tickers, start, end):
    """Download historical adjusted close prices."""
    all_data = pd.DataFrame()

    progress_bar = st.progress(0)
    status_text = st.empty()

    failed_tickers = []

    for i, ticker in enumerate(tickers):
        status_text.text(f"Downloading {ticker}...")
        try:
            d = yf.download(ticker, start=start, end=end, progress=False, auto_adjust=False)
            if "Adj Close" in d.columns and not d.empty:
                d = d[["Adj Close"]].rename(columns={"Adj Close": ticker})
                all_data = pd.concat([all_data, d], axis=1)
            else:
                failed_tickers.append(ticker)
                st.warning(f"No data available for {ticker}")
        except Exception as e:
            failed_tickers.append(ticker)
            st.warning(f"Failed to download {ticker}: {str(e)[:100]}")

        progress_bar.progress((i + 1) / len(tickers))

    status_text.empty()
    progress_bar.empty()

    if failed_tickers:
        st.info(f"📊 Successfully loaded {len(tickers) - len(failed_tickers)}/{len(tickers)} tickers")

    # Drop rows with any NaN values to ensure alignment
    if not all_data.empty:
        initial_rows = len(all_data)
        all_data = all_data.dropna()
        if len(all_data) < initial_rows:
            st.info(f"📅 Aligned data: {len(all_data)} trading days with complete data for all tickers")

    return all_data


def compute_portfolio(prices, weights, rebalance="none"):
    """Compute portfolio value over time."""
    weights = np.array(weights)
    weights = weights / weights.sum()
    prices = prices.dropna()

    if len(prices.columns) != len(weights):
        missing_tickers = len(weights) - len(prices.columns)
        st.warning(f"⚠️ Warning: {missing_tickers} ticker(s) missing. Adjusting weights proportionally.")
        weights = weights[:len(prices.columns)]
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


def calculate_metrics(portfolio):
    """Calculate portfolio performance metrics."""
    total_return = portfolio.iloc[-1] / portfolio.iloc[0] - 1
    daily_rets = portfolio.pct_change().dropna()

    # Calculate annualized return using actual calendar days
    num_days = (portfolio.index[-1] - portfolio.index[0]).days
    num_years = num_days / 365.25
    annualized_return = (1 + total_return) ** (1 / num_years) - 1 if num_years > 0 else 0

    annualized_vol = daily_rets.std() * np.sqrt(252)
    running_max = portfolio.cummax()
    drawdowns = (portfolio - running_max) / running_max
    max_dd = drawdowns.min()

    return {
        'Total Return': f"{total_return:.2%}",
        'Annualized Return': f"{annualized_return:.2%}",
        'Annualized Volatility': f"{annualized_vol:.2%}",
        'Max Drawdown': f"{max_dd:.2%}",
        'Period': f"{portfolio.index[0].date()} to {portfolio.index[-1].date()}"
    }




# Custom Portfolio Builder
if portfolio_mode == "Custom Portfolio Builder":
    st.header("🔧 Custom Portfolio Builder")

    st.markdown("**Build your own portfolio by adding tickers and weights:**")

    col1, col2, col3 = st.columns([3, 2, 1])

    with col1:
        new_ticker = st.text_input("Add Ticker Symbol", placeholder="e.g., AAPL, MSFT, SPY", key="new_ticker_input").upper()
    with col2:
        new_weight = st.number_input("Weight (%)", min_value=0.0, max_value=100.0, value=10.0, step=1.0, key="new_weight_input")
    with col3:
        st.write("")
        st.write("")
        if st.button("➕ Add", use_container_width=True):
            if new_ticker and new_ticker not in st.session_state.custom_tickers:
                st.session_state.custom_tickers.append(new_ticker)
                st.session_state.custom_weights.append(new_weight)
                st.rerun()
            elif new_ticker in st.session_state.custom_tickers:
                st.warning(f"⚠️ {new_ticker} already in portfolio")

    st.markdown("---")

    # Display current portfolio
    if len(st.session_state.custom_tickers) > 0:
        st.subheader("Current Portfolio Composition")

        # Create editable portfolio table
        portfolio_data = []
        for i, (ticker, weight) in enumerate(zip(st.session_state.custom_tickers, st.session_state.custom_weights)):
            portfolio_data.append({
                'Index': i,
                'Ticker': ticker,
                'Weight (%)': weight,
                'Normalized Weight (%)': 0  # Will calculate below
            })

        # Calculate normalized weights
        total_weight = sum(st.session_state.custom_weights)
        for item in portfolio_data:
            item['Normalized Weight (%)'] = (item['Weight (%)'] / total_weight * 100) if total_weight > 0 else 0

        # Display portfolio
        col1, col2 = st.columns([3, 1])

        with col1:
            for i, item in enumerate(portfolio_data):
                cols = st.columns([2, 2, 2, 1])
                with cols[0]:
                    st.write(f"**{item['Ticker']}**")
                with cols[1]:
                    new_weight_val = st.number_input(
                        "Weight",
                        min_value=0.0,
                        max_value=100.0,
                        value=float(item['Weight (%)']),
                        step=1.0,
                        key=f"weight_{i}",
                        label_visibility="collapsed"
                    )
                    if new_weight_val != item['Weight (%)']:
                        st.session_state.custom_weights[i] = new_weight_val
                        st.rerun()
                with cols[2]:
                    st.write(f"{item['Normalized Weight (%)']:.2f}%")
                with cols[3]:
                    if st.button("🗑️", key=f"delete_{i}", use_container_width=True):
                        st.session_state.custom_tickers.pop(i)
                        st.session_state.custom_weights.pop(i)
                        st.rerun()

        with col2:
            st.metric("Total Weight", f"{total_weight:.1f}%")
            if not np.isclose(total_weight, 100.0, atol=0.1):
                st.warning("⚠️ Weights will be normalized")
            else:
                st.success("✅ Weights sum to 100%")

            if st.button("🔄 Normalize All", use_container_width=True):
                if total_weight > 0:
                    st.session_state.custom_weights = [w / total_weight * 100 for w in st.session_state.custom_weights]
                    st.rerun()

            if st.button("🗑️ Clear All", use_container_width=True):
                st.session_state.custom_tickers = []
                st.session_state.custom_weights = []
                st.rerun()

        st.markdown("---")

        # Run backtest on custom portfolio
        if len(st.session_state.custom_tickers) > 0:
            st.header("📊 Custom Portfolio Analysis")

            # Normalize weights to array
            weights_array = np.array(st.session_state.custom_weights)
            weights_array = weights_array / weights_array.sum()

            # Current market data
            st.subheader("Current Market Data")
            current_data = get_current_prices(st.session_state.custom_tickers)
            st.dataframe(current_data, use_container_width=True, hide_index=True)

            # Historical performance
            st.subheader("Historical Performance")
            with st.spinner("Loading historical data..."):
                prices = get_historical_prices(st.session_state.custom_tickers, START, END)

                if not prices.empty:
                    portfolio = compute_portfolio(prices, weights_array, rebalance=rebalance_option)
                    metrics = calculate_metrics(portfolio)

                    # Save to database
                    database.save_to_database(st.session_state.custom_tickers, st.session_state.custom_weights,
                                   "Custom Portfolio", years_back, rebalance_option, metrics)

                    # Display metrics
                    cols = st.columns(4)
                    cols[0].metric("Total Return", metrics['Total Return'])
                    cols[1].metric("Annualized Return", metrics['Annualized Return'])
                    cols[2].metric("Volatility", metrics['Annualized Volatility'])
                    cols[3].metric("Max Drawdown", metrics['Max Drawdown'])

                    # AI Portfolio Advisor
                    st.markdown("---")
                    st.subheader("🤖 AI Portfolio Advisor")

                    with st.expander("📊 Get AI Analysis", expanded=False):
                        if st.button("🔍 Analyze Portfolio with AI", key="analyze_custom", use_container_width=True):
                            with st.spinner("AI is analyzing your portfolio..."):
                                result = ai_advisor.analyze_portfolio(
                                    st.session_state.custom_tickers,
                                    st.session_state.custom_weights,
                                    metrics,
                                    "Custom Portfolio"
                                )

                                if result['success']:
                                    st.success("✅ Analysis Complete!")
                                    st.markdown(result['analysis'])
                                    st.caption(f"Analysis generated at {result['timestamp']} | Tokens used: {result['tokens_used']}")
                                else:
                                    st.error(f"❌ {result['error']}")
                                    if 'setup_instructions' in result:
                                        st.info(f"ℹ️ {result['setup_instructions']}")

                                    # Show fallback insights
                                    st.markdown("**Quick Insights (Rule-based):**")
                                    st.info(ai_advisor.get_quick_insights(metrics))

                    # Plot
                    fig, ax = plt.subplots(figsize=(12, 6))
                    ax.plot(portfolio.index, portfolio, label='Custom Portfolio', linewidth=2, color='purple')
                    ax.set_title(f"Custom Portfolio - Cumulative Performance ({years_back}Y)", fontsize=14, fontweight='bold')
                    ax.set_xlabel("Date", fontsize=12)
                    ax.set_ylabel("Cumulative Return (normalized to 1)", fontsize=12)
                    ax.grid(True, alpha=0.3)
                    ax.legend(fontsize=12)
                    plt.tight_layout()
                    st.pyplot(fig)

                    # Export data
                    col1, col2 = st.columns(2)
                    with col1:
                        csv_data = pd.DataFrame({
                            'Date': portfolio.index,
                            'Portfolio Value': portfolio.values
                        })
                        st.download_button(
                            label="📥 Download Portfolio Data (CSV)",
                            data=csv_data.to_csv(index=False),
                            file_name=f"custom_portfolio_{datetime.now().strftime('%Y%m%d')}.csv",
                            mime="text/csv",
                            use_container_width=True
                        )
                    with col2:
                        config_data = pd.DataFrame({
                            'Ticker': st.session_state.custom_tickers,
                            'Weight': st.session_state.custom_weights
                        })
                        st.download_button(
                            label="📥 Download Configuration (CSV)",
                            data=config_data.to_csv(index=False),
                            file_name=f"portfolio_config_{datetime.now().strftime('%Y%m%d')}.csv",
                            mime="text/csv",
                            use_container_width=True
                        )
                else:
                    st.error("Failed to load historical data")

else:
    # Main content
    tab1, tab2 = st.tabs(["📈 WDI Portfolio", "📈 GOF Portfolio"])

    with tab1:
        st.header("WDI Variant Portfolio")

        col1, col2 = st.columns([2, 1])

        with col1:
            st.subheader("Current Market Data")
            current_data_wdi = get_current_prices(TICKERS_WDI)
            st.dataframe(current_data_wdi, use_container_width=True, hide_index=True)

        with col2:
            st.subheader("Portfolio Weights")
            weights_df = pd.DataFrame({
                'Ticker': TICKERS_WDI,
                'Weight': [f"{w:.1%}" for w in WEIGHTS]
            })
            st.dataframe(weights_df, use_container_width=True, hide_index=True)

        st.subheader("Historical Performance")

        with st.spinner("Loading historical data..."):
            prices_wdi = get_historical_prices(TICKERS_WDI, START, END)

            if not prices_wdi.empty:
                try:
                    portfolio_wdi = compute_portfolio(prices_wdi, WEIGHTS, rebalance=rebalance_option)
                    metrics_wdi = calculate_metrics(portfolio_wdi)

                    # Save to database
                    database.save_to_database(TICKERS_WDI, WEIGHTS, "WDI Portfolio", years_back, rebalance_option, metrics_wdi)

                    # Display metrics
                    cols = st.columns(4)
                    cols[0].metric("Total Return", metrics_wdi['Total Return'])
                    cols[1].metric("Annualized Return", metrics_wdi['Annualized Return'])
                    cols[2].metric("Volatility", metrics_wdi['Annualized Volatility'])
                    cols[3].metric("Max Drawdown", metrics_wdi['Max Drawdown'])

                    # AI Portfolio Advisor
                    st.markdown("---")
                    with st.expander("🤖 Get AI Analysis", expanded=False):
                        if st.button("🔍 Analyze WDI Portfolio with AI", key="analyze_wdi", use_container_width=True):
                            with st.spinner("AI is analyzing your portfolio..."):
                                result = ai_advisor.analyze_portfolio(
                                    TICKERS_WDI,
                                    (WEIGHTS * 100).tolist(),
                                    metrics_wdi,
                                    "WDI Portfolio"
                                )

                                if result['success']:
                                    st.success("✅ Analysis Complete!")
                                    st.markdown(result['analysis'])
                                    st.caption(f"Analysis generated at {result['timestamp']} | Tokens used: {result['tokens_used']}")
                                else:
                                    st.error(f"❌ {result['error']}")
                                    if 'setup_instructions' in result:
                                        st.info(f"ℹ️ {result['setup_instructions']}")
                                    st.markdown("**Quick Insights (Rule-based):**")
                                    st.info(ai_advisor.get_quick_insights(metrics_wdi))

                    # Plot
                    fig, ax = plt.subplots(figsize=(12, 6))
                    ax.plot(portfolio_wdi.index, portfolio_wdi, label='WDI Portfolio', linewidth=2)
                    ax.set_title(f"WDI Portfolio - Cumulative Performance ({years_back}Y)", fontsize=14, fontweight='bold')
                    ax.set_xlabel("Date", fontsize=12)
                    ax.set_ylabel("Cumulative Return (normalized to 1)", fontsize=12)
                    ax.grid(True, alpha=0.3)
                    ax.legend(fontsize=12)
                    plt.tight_layout()
                    st.pyplot(fig)
                except Exception as e:
                    st.error(f"❌ Error computing WDI portfolio: {str(e)}")
                    st.info(f"Data shape: {prices_wdi.shape}, Columns: {list(prices_wdi.columns)}")
            else:
                st.error("❌ Failed to load historical data for WDI portfolio. No data returned.")

    with tab2:
        st.header("GOF Variant Portfolio")

        col1, col2 = st.columns([2, 1])

        with col1:
            st.subheader("Current Market Data")
            current_data_gof = get_current_prices(TICKERS_GOF)
            st.dataframe(current_data_gof, use_container_width=True, hide_index=True)

        with col2:
            st.subheader("Portfolio Weights")
            weights_df = pd.DataFrame({
                'Ticker': TICKERS_GOF,
                'Weight': [f"{w:.1%}" for w in WEIGHTS]
            })
            st.dataframe(weights_df, use_container_width=True, hide_index=True)

        st.subheader("Historical Performance")

        with st.spinner("Loading historical data..."):
            prices_gof = get_historical_prices(TICKERS_GOF, START, END)

            if not prices_gof.empty:
                try:
                    portfolio_gof = compute_portfolio(prices_gof, WEIGHTS, rebalance=rebalance_option)
                    metrics_gof = calculate_metrics(portfolio_gof)

                    # Save to database
                    database.save_to_database(TICKERS_GOF, WEIGHTS, "GOF Portfolio", years_back, rebalance_option, metrics_gof)

                    # Display metrics
                    cols = st.columns(4)
                    cols[0].metric("Total Return", metrics_gof['Total Return'])
                    cols[1].metric("Annualized Return", metrics_gof['Annualized Return'])
                    cols[2].metric("Volatility", metrics_gof['Annualized Volatility'])
                    cols[3].metric("Max Drawdown", metrics_gof['Max Drawdown'])

                    # AI Portfolio Advisor
                    st.markdown("---")
                    with st.expander("🤖 Get AI Analysis", expanded=False):
                        if st.button("🔍 Analyze GOF Portfolio with AI", key="analyze_gof", use_container_width=True):
                            with st.spinner("AI is analyzing your portfolio..."):
                                result = ai_advisor.analyze_portfolio(
                                    TICKERS_GOF,
                                    (WEIGHTS * 100).tolist(),
                                    metrics_gof,
                                    "GOF Portfolio"
                                )

                                if result['success']:
                                    st.success("✅ Analysis Complete!")
                                    st.markdown(result['analysis'])
                                    st.caption(f"Analysis generated at {result['timestamp']} | Tokens used: {result['tokens_used']}")
                                else:
                                    st.error(f"❌ {result['error']}")
                                    if 'setup_instructions' in result:
                                        st.info(f"ℹ️ {result['setup_instructions']}")
                                    st.markdown("**Quick Insights (Rule-based):**")
                                    st.info(ai_advisor.get_quick_insights(metrics_gof))

                    # Plot
                    fig, ax = plt.subplots(figsize=(12, 6))
                    ax.plot(portfolio_gof.index, portfolio_gof, label='GOF Portfolio', linewidth=2, color='green')
                    ax.set_title(f"GOF Portfolio - Cumulative Performance ({years_back}Y)", fontsize=14, fontweight='bold')
                    ax.set_xlabel("Date", fontsize=12)
                    ax.set_ylabel("Cumulative Return (normalized to 1)", fontsize=12)
                    ax.grid(True, alpha=0.3)
                    ax.legend(fontsize=12)
                    plt.tight_layout()
                    st.pyplot(fig)
                except Exception as e:
                    st.error(f"❌ Error computing GOF portfolio: {str(e)}")
                    st.info(f"Data shape: {prices_gof.shape}, Columns: {list(prices_gof.columns)}")
            else:
                st.error("❌ Failed to load historical data for GOF portfolio. No data returned.")

    # Comparison section
    st.header("📊 Side-by-Side Comparison")
    if 'portfolio_wdi' in locals() and 'portfolio_gof' in locals():
        col1, col2 = st.columns(2)

        with col1:
            st.subheader("WDI Metrics")
            for key, value in metrics_wdi.items():
                if key != 'Period':
                    st.metric(key, value)

        with col2:
            st.subheader("GOF Metrics")
            for key, value in metrics_gof.items():
                if key != 'Period':
                    st.metric(key, value)

        # Combined chart
        st.subheader("Combined Performance Chart")
        fig, ax = plt.subplots(figsize=(14, 7))
        ax.plot(portfolio_wdi.index, portfolio_wdi, label='WDI Portfolio', linewidth=2)
        ax.plot(portfolio_gof.index, portfolio_gof, label='GOF Portfolio', linewidth=2)
        ax.set_title(f"Portfolio Comparison - Cumulative Performance ({years_back}Y)", fontsize=14, fontweight='bold')
        ax.set_xlabel("Date", fontsize=12)
        ax.set_ylabel("Cumulative Return (normalized to 1)", fontsize=12)
        ax.grid(True, alpha=0.3)
        ax.legend(fontsize=12)
        plt.tight_layout()
        st.pyplot(fig)

# Footer
st.markdown("---")
st.caption("💡 Tip: Adjust the years and rebalancing options in the sidebar. Refresh the page to update market data.")

