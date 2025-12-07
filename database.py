"""
Database module supporting both SQLite (local) and PostgreSQL (cloud)
"""

import os
import json
import sqlite3
from datetime import datetime
from dotenv import load_dotenv
import pandas as pd
import numpy as np

# Load environment variables
load_dotenv()

# Database configuration
DB_TYPE = os.getenv('DB_TYPE', 'sqlite')  # 'sqlite' or 'postgres'

if DB_TYPE == 'postgres':
    import psycopg2
    from psycopg2.extras import RealDictCursor

    # PostgreSQL connection parameters
    DB_CONFIG = {
        'host': os.getenv('DB_HOST'),
        'port': os.getenv('DB_PORT', 5432),
        'database': os.getenv('DB_NAME', 'postgres'),
        'user': os.getenv('DB_USER'),
        'password': os.getenv('DB_PASSWORD'),
        'sslmode': os.getenv('DB_SSL_MODE', 'require')
    }

    # Add SSL certificate if provided
    ssl_cert = os.getenv('DB_SSL_CERT')
    if ssl_cert and os.path.exists(ssl_cert):
        DB_CONFIG['sslrootcert'] = ssl_cert
else:
    # SQLite configuration
    DB_PATH = "portfolio_history.db"


def get_connection():
    """Get database connection based on DB_TYPE."""
    if DB_TYPE == 'postgres':
        return psycopg2.connect(**DB_CONFIG)
    else:
        return sqlite3.connect(DB_PATH)


def init_database():
    """Initialize database and create tables if they don't exist."""
    conn = get_connection()
    cursor = conn.cursor()

    if DB_TYPE == 'postgres':
        # PostgreSQL schema
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS search_history (
                id SERIAL PRIMARY KEY,
                timestamp TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                portfolio_name VARCHAR(255) NOT NULL,
                tickers JSONB NOT NULL,
                weights JSONB NOT NULL,
                years_back INTEGER,
                rebalance_option VARCHAR(50)
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS portfolio_metrics (
                id SERIAL PRIMARY KEY,
                search_id INTEGER REFERENCES search_history(id) ON DELETE CASCADE,
                total_return VARCHAR(50),
                annualized_return VARCHAR(50),
                annualized_volatility VARCHAR(50),
                max_drawdown VARCHAR(50),
                period VARCHAR(255)
            )
        ''')

        # Create indexes for better query performance
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_search_history_timestamp
            ON search_history(timestamp DESC)
        ''')
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_portfolio_metrics_search_id
            ON portfolio_metrics(search_id)
        ''')

    else:
        # SQLite schema
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS search_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                portfolio_name TEXT NOT NULL,
                tickers TEXT NOT NULL,
                weights TEXT NOT NULL,
                years_back INTEGER,
                rebalance_option TEXT
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS portfolio_metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                search_id INTEGER,
                total_return TEXT,
                annualized_return TEXT,
                annualized_volatility TEXT,
                max_drawdown TEXT,
                period TEXT,
                FOREIGN KEY (search_id) REFERENCES search_history (id)
            )
        ''')

    conn.commit()
    conn.close()


def save_to_database(tickers, weights, portfolio_name="Custom", years_back=5, rebalance_option="none", metrics=None):
    """Save portfolio search to database."""
    conn = get_connection()
    cursor = conn.cursor()

    timestamp = datetime.now()

    if DB_TYPE == 'postgres':
        # PostgreSQL uses JSONB for arrays
        tickers_data = tickers if isinstance(tickers, list) else list(tickers)
        weights_data = weights.tolist() if isinstance(weights, np.ndarray) else weights

        cursor.execute('''
            INSERT INTO search_history (timestamp, portfolio_name, tickers, weights, years_back, rebalance_option)
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING id
        ''', (timestamp, portfolio_name, json.dumps(tickers_data), json.dumps(weights_data), years_back, rebalance_option))

        search_id = cursor.fetchone()[0]

        # Save metrics if provided
        if metrics:
            cursor.execute('''
                INSERT INTO portfolio_metrics (search_id, total_return, annualized_return, annualized_volatility, max_drawdown, period)
                VALUES (%s, %s, %s, %s, %s, %s)
            ''', (search_id, metrics.get('Total Return'), metrics.get('Annualized Return'),
                  metrics.get('Annualized Volatility'), metrics.get('Max Drawdown'), metrics.get('Period')))

    else:
        # SQLite uses JSON strings
        timestamp_str = timestamp.strftime('%Y-%m-%d %H:%M:%S')
        tickers_json = json.dumps(tickers if isinstance(tickers, list) else list(tickers))
        weights_json = json.dumps(weights.tolist() if isinstance(weights, np.ndarray) else weights)

        cursor.execute('''
            INSERT INTO search_history (timestamp, portfolio_name, tickers, weights, years_back, rebalance_option)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (timestamp_str, portfolio_name, tickers_json, weights_json, years_back, rebalance_option))

        search_id = cursor.lastrowid

        # Save metrics if provided
        if metrics:
            cursor.execute('''
                INSERT INTO portfolio_metrics (search_id, total_return, annualized_return, annualized_volatility, max_drawdown, period)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (search_id, metrics.get('Total Return'), metrics.get('Annualized Return'),
                  metrics.get('Annualized Volatility'), metrics.get('Max Drawdown'), metrics.get('Period')))

    conn.commit()
    conn.close()


def load_history_from_database(limit=100):
    """Load search history from database."""
    try:
        conn = get_connection()

        if DB_TYPE == 'postgres':
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            cursor.execute('''
                SELECT id, timestamp, portfolio_name, tickers, weights, years_back, rebalance_option
                FROM search_history
                ORDER BY timestamp DESC
                LIMIT %s
            ''', (limit,))
            rows = cursor.fetchall()

            history = []
            for row in rows:
                history.append({
                    'id': row['id'],
                    'timestamp': row['timestamp'].strftime('%Y-%m-%d %H:%M:%S'),
                    'portfolio_name': row['portfolio_name'],
                    'tickers': row['tickers'],  # Already parsed from JSONB
                    'weights': row['weights'],  # Already parsed from JSONB
                    'years_back': row['years_back'],
                    'rebalance_option': row['rebalance_option']
                })
        else:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT id, timestamp, portfolio_name, tickers, weights, years_back, rebalance_option
                FROM search_history
                ORDER BY timestamp DESC
                LIMIT ?
            ''', (limit,))
            rows = cursor.fetchall()

            history = []
            for row in rows:
                history.append({
                    'id': row[0],
                    'timestamp': row[1],
                    'portfolio_name': row[2],
                    'tickers': json.loads(row[3]),
                    'weights': json.loads(row[4]),
                    'years_back': row[5],
                    'rebalance_option': row[6]
                })

        conn.close()
        return history
    except Exception as e:
        print(f"Error loading history: {e}")
        return []


def get_portfolio_metrics(search_id):
    """Get metrics for a specific search."""
    try:
        conn = get_connection()

        if DB_TYPE == 'postgres':
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            cursor.execute('''
                SELECT total_return, annualized_return, annualized_volatility, max_drawdown, period
                FROM portfolio_metrics
                WHERE search_id = %s
            ''', (search_id,))
            row = cursor.fetchone()

            if row:
                return {
                    'Total Return': row['total_return'],
                    'Annualized Return': row['annualized_return'],
                    'Annualized Volatility': row['annualized_volatility'],
                    'Max Drawdown': row['max_drawdown'],
                    'Period': row['period']
                }
        else:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT total_return, annualized_return, annualized_volatility, max_drawdown, period
                FROM portfolio_metrics
                WHERE search_id = ?
            ''', (search_id,))
            row = cursor.fetchone()

            if row:
                return {
                    'Total Return': row[0],
                    'Annualized Return': row[1],
                    'Annualized Volatility': row[2],
                    'Max Drawdown': row[3],
                    'Period': row[4]
                }

        conn.close()
        return None
    except Exception as e:
        print(f"Error getting metrics: {e}")
        return None


def clear_database_history():
    """Clear all history from database."""
    try:
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute('DELETE FROM portfolio_metrics')
        cursor.execute('DELETE FROM search_history')

        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Error clearing history: {e}")


def export_history_to_csv():
    """Export database history to CSV format."""
    history = load_history_from_database(limit=10000)
    if history:
        df = pd.DataFrame(history)
        df['tickers'] = df['tickers'].apply(lambda x: ', '.join(x))
        df['weights'] = df['weights'].apply(lambda x: ', '.join([str(w) for w in x]))
        return df.to_csv(index=False)
    return ""


def get_database_stats():
    """Get database statistics."""
    try:
        conn = get_connection()
        cursor = conn.cursor()

        if DB_TYPE == 'postgres':
            cursor.execute("SELECT COUNT(*) FROM search_history")
        else:
            cursor.execute("SELECT COUNT(*) FROM search_history")

        total = cursor.fetchone()[0]
        conn.close()

        return {
            'total_searches': total,
            'db_type': DB_TYPE,
            'db_host': DB_CONFIG.get('host') if DB_TYPE == 'postgres' else 'local'
        }
    except Exception as e:
        print(f"Error getting stats: {e}")
        return {'total_searches': 0, 'db_type': DB_TYPE, 'db_host': 'unknown'}
