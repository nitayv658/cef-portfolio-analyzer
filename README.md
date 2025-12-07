# CEF Portfolio Analyzer

A comprehensive portfolio backtesting and analysis tool for equity and derivatives traders, with a focus on Closed-End Funds (CEFs) and dividend income strategies.

![Portfolio Dashboard](https://img.shields.io/badge/Python-3.8%2B-blue)
![Streamlit](https://img.shields.io/badge/Streamlit-1.28%2B-red)
![License](https://img.shields.io/badge/License-MIT-green)

## Overview

CEF Portfolio Analyzer is a powerful Python-based application that enables traders to backtest portfolios, analyze historical performance, and build custom investment strategies in real-time. Built with Streamlit for an interactive web interface and powered by yfinance for market data, it provides professional-grade analytics for both preset and custom portfolios.

## Features

### 📊 Real-Time Custom Portfolio Builder
- Add any ticker symbol (stocks, ETFs, CEFs, derivatives)
- Dynamic weight allocation with auto-normalization
- Live market data including bid/ask spreads and dividend yields
- Interactive portfolio composition management
- Edit weights on the fly with instant recalculation

### 📈 Advanced Backtesting
- Historical performance analysis (1-10 years)
- Multiple rebalancing strategies:
  - **Buy-and-Hold**: No rebalancing
  - **Monthly Rebalancing**: Automatic monthly portfolio rebalancing
- Comprehensive performance metrics:
  - Total Return
  - Annualized Return (calendar-day adjusted)
  - Annualized Volatility
  - Maximum Drawdown
- Visual performance charts with customizable timeframes

### 🎯 Preset Portfolio Analysis
- Pre-configured CEF portfolios (WDI and GOF variants)
- Side-by-side portfolio comparison
- Combined performance visualization
- Real-time market data monitoring

### 💾 Data Export & History
- Download portfolio performance data as CSV
- Export portfolio configurations for documentation
- Timestamped files for version control
- **Flexible database backend** (SQLite for local, PostgreSQL for cloud)
- Track all portfolio analyses with performance metrics
- View recent searches in sidebar with metrics preview
- Cloud database support (Supabase, Neon, Railway)

### 🤖 AI Portfolio Advisor
- **Claude-powered intelligent analysis** of your portfolios
- Natural language insights and recommendations
- Strengths and weaknesses identification
- Risk assessment and scoring
- Actionable improvement suggestions
- Fallback rule-based analysis when AI unavailable

### 🔧 Technical Features
- Smart caching for optimal performance
- Error handling with detailed diagnostics
- Data validation and alignment
- Progress indicators during data loading
- Responsive UI optimized for trading workflows
- **Dual database support**: SQLite (local) or PostgreSQL (cloud)

## Installation

### Prerequisites
- Python 3.8 or higher
- pip package manager

### Setup

1. **Clone the repository**
```bash
git clone https://github.com/yourusername/cef-portfolio-analyzer.git
cd cef-portfolio-analyzer
```

2. **Install dependencies**
```bash
pip install -r requirements.txt
```

3. **Configure database** (optional - uses SQLite by default)

For local development with SQLite (no configuration needed):
- The app will automatically create `portfolio_history.db`

For cloud deployment with PostgreSQL:
```bash
# Copy the environment template
cp .env.example .env

# Edit .env and add your database credentials
# DB_TYPE=postgres
# DB_HOST=your-project.supabase.co
# DB_PORT=5432
# DB_NAME=postgres
# DB_USER=postgres
# DB_PASSWORD=your-password
# DB_SSL_MODE=require
```

Supported cloud database providers:
- [Supabase](https://supabase.com/) - PostgreSQL with generous free tier
- [Neon](https://neon.tech/) - Serverless PostgreSQL
- [Railway](https://railway.app/) - Easy database deployment

For AI Portfolio Advisor (optional):
```bash
# Add to your .env file
ANTHROPIC_API_KEY=your-api-key-here
```
Get your API key from [Anthropic Console](https://console.anthropic.com/)

4. **Run the Streamlit app**
```bash
streamlit run portfolio_app.py
```

The app will open in your default browser at `http://localhost:8501`

### Alternative: CLI Backtesting

For command-line backtesting without the web interface:
```bash
python portfolio_backtest.py
```

This will generate performance charts and CSV files for the preset portfolios.

### Database Management

View and manage your portfolio search history:
```bash
python db_viewer.py
```

This interactive tool allows you to:
- View all searches with metrics
- Export history to CSV
- View statistics
- Delete specific searches
- Clear all history

## Usage

### Custom Portfolio Builder

1. **Launch the app**
   ```bash
   streamlit run portfolio_app.py
   ```

2. **Select "Custom Portfolio Builder"** in the sidebar

3. **Build your portfolio**
   - Enter a ticker symbol (e.g., AAPL, SPY, PDI)
   - Set the weight percentage
   - Click "➕ Add"
   - Repeat for all holdings

4. **Adjust settings**
   - Use the sidebar to select historical timeframe (1-10 years)
   - Choose rebalancing strategy (monthly or none)

5. **View results**
   - Real-time market data updates
   - Historical performance metrics
   - Interactive performance chart

6. **Export data**
   - Download portfolio performance as CSV
   - Save configuration for future reference

### Preset Portfolios

1. Select "Preset Portfolios" in the sidebar
2. Choose between WDI or GOF portfolio tabs
3. View current market data and performance metrics
4. Compare both portfolios side-by-side

### Search History

All portfolio analyses are automatically saved to your configured database (SQLite or PostgreSQL):
- View recent searches in the sidebar
- See performance metrics for past searches
- Export full history to CSV
- Clear history when needed
- Use `db_viewer.py` for advanced database management
- Cloud database enables access across multiple devices

## Project Structure

```
cef-portfolio-analyzer/
├── portfolio_app.py           # Streamlit web application
├── portfolio_backtest.py      # CLI backtesting script
├── database.py                # Database abstraction layer (SQLite/PostgreSQL)
├── ai_advisor.py              # AI portfolio analysis module (Claude API)
├── db_viewer.py               # Database viewer/management tool
├── test_db_connection.py      # Database connection test script
├── requirements.txt           # Python dependencies
├── .env.example               # Environment variables template
├── .env                       # Your credentials (not in git)
├── README.md                  # Project documentation
├── portfolio_history.db       # SQLite database (auto-created, local only)
├── examples/                  # Example scripts
│   └── nitay.py              # Async fetching example
└── *.png, *.csv              # Generated output files
```

## Configuration

### Database Configuration

The application supports two database backends:

**SQLite (Default - Local Development)**
- No configuration required
- Database file created automatically as `portfolio_history.db`
- Perfect for local development and single-user scenarios

**PostgreSQL (Cloud - Production)**
1. Create a PostgreSQL database on [Supabase](https://supabase.com/), [Neon](https://neon.tech/), or [Railway](https://railway.app/)
2. Copy `.env.example` to `.env`
3. Configure your database credentials:
   ```bash
   DB_TYPE=postgres
   DB_HOST=your-project.supabase.co
   DB_PORT=5432
   DB_NAME=postgres
   DB_USER=postgres
   DB_PASSWORD=your-password
   DB_SSL_MODE=require
   ```
4. Test the connection:
   ```bash
   python3 test_db_connection.py
   ```

### Preset Portfolios

Edit the configuration in `portfolio_app.py` or `portfolio_backtest.py`:

```python
# Portfolio tickers
TICKERS_WDI = ["PDI", "BIT", "DSL", "KIO", "EVV", "WDI"]
TICKERS_GOF = ["PDI", "BIT", "DSL", "KIO", "EVV", "GOF"]

# Portfolio weights (must sum to 1.0)
WEIGHTS = np.array([0.25, 0.15, 0.15, 0.15, 0.15, 0.15])
```

## Use Cases

### For Equity Traders
- Backtest stock portfolio strategies
- Compare different allocation schemes
- Analyze risk-adjusted returns

### For Income Investors
- Analyze CEF portfolios focused on dividend yield
- Track distribution yields and spreads
- Monitor premium/discount to NAV

### For Derivatives Traders
- Model complex multi-asset positions
- Test hedging strategies
- Analyze correlation and diversification

### For Portfolio Managers
- Professional-grade analytics
- Client portfolio analysis
- Performance reporting and visualization

## Performance Metrics Explained

- **Total Return**: Cumulative return over the entire period
- **Annualized Return**: Geometric mean annual return (calendar-day adjusted)
- **Annualized Volatility**: Standard deviation of daily returns, annualized
- **Max Drawdown**: Largest peak-to-trough decline during the period

## Technology Stack

- **Python 3.8+** - Core programming language
- **Streamlit 1.28+** - Interactive web interface
- **yfinance** - Real-time and historical market data
- **Pandas & NumPy** - Data manipulation and numerical computing
- **Matplotlib** - Performance visualization
- **SQLite / PostgreSQL** - Flexible database backend
- **psycopg2** - PostgreSQL adapter for cloud deployment
- **python-dotenv** - Environment variable management
- **Anthropic Claude API** - AI-powered portfolio analysis
- **anthropic** - Official Anthropic Python SDK

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- Built with [Streamlit](https://streamlit.io/)
- Market data powered by [yfinance](https://github.com/ranaroussi/yfinance)
- Developed for equity and derivatives traders

## Support

For issues, questions, or suggestions, please open an issue on GitHub.

## Roadmap

Future enhancements planned:
- [ ] Sharpe ratio and Sortino ratio
- [ ] Correlation matrix visualization
- [ ] Benchmark comparison (SPY, AGG)
- [ ] Rolling returns analysis
- [ ] Value at Risk (VaR) calculations
- [ ] CEF premium/discount tracking
- [ ] Monte Carlo simulation

---

**Built for traders, by traders.**