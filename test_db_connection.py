"""
Test script to verify cloud database connection
"""
import database

def test_connection():
    """Test PostgreSQL connection and table creation."""
    print("Testing cloud database connection...")
    print(f"Database type: {database.DB_TYPE}")

    if database.DB_TYPE == 'postgres':
        print(f"Host: {database.DB_CONFIG['host']}")
        print(f"Database: {database.DB_CONFIG['database']}")
        print(f"SSL Mode: {database.DB_CONFIG['sslmode']}")

    try:
        # Test connection
        print("\n1. Testing connection...")
        conn = database.get_connection()
        print("✓ Connection successful!")
        conn.close()

        # Initialize database
        print("\n2. Initializing database tables...")
        database.init_database()
        print("✓ Tables created successfully!")

        # Get database stats
        print("\n3. Getting database statistics...")
        stats = database.get_database_stats()
        print(f"✓ Total searches: {stats['total_searches']}")
        print(f"✓ DB Type: {stats['db_type']}")
        print(f"✓ DB Host: {stats['db_host']}")

        # Test insert
        print("\n4. Testing data insert...")
        database.save_to_database(
            tickers=['SPY', 'AGG'],
            weights=[60.0, 40.0],
            portfolio_name="Test Portfolio",
            years_back=5,
            rebalance_option="none",
            metrics={
                'Total Return': '50.00%',
                'Annualized Return': '8.45%',
                'Annualized Volatility': '12.34%',
                'Max Drawdown': '-15.67%',
                'Period': '2020-01-01 to 2025-01-01'
            }
        )
        print("✓ Data inserted successfully!")

        # Test retrieve
        print("\n5. Testing data retrieval...")
        history = database.load_history_from_database(limit=5)
        print(f"✓ Retrieved {len(history)} records")

        if history:
            latest = history[0]
            print(f"\nLatest record:")
            print(f"  Portfolio: {latest['portfolio_name']}")
            print(f"  Tickers: {latest['tickers']}")
            print(f"  Weights: {latest['weights']}")
            print(f"  Timestamp: {latest['timestamp']}")

            # Get metrics
            metrics = database.get_portfolio_metrics(latest['id'])
            if metrics:
                print(f"\n  Metrics:")
                print(f"    Total Return: {metrics['Total Return']}")
                print(f"    Annualized Return: {metrics['Annualized Return']}")

        print("\n" + "="*50)
        print("✓ All tests passed! Cloud database is ready to use.")
        print("="*50)

    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

    return True

if __name__ == "__main__":
    test_connection()
