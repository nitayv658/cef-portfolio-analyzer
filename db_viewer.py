"""
Database Viewer for Portfolio History
Simple script to view and manage the portfolio search history database.
"""

import sqlite3
import pandas as pd
import json

DB_PATH = "portfolio_history.db"


def view_all_searches():
    """Display all searches from the database."""
    conn = sqlite3.connect(DB_PATH)

    query = """
        SELECT
            h.id,
            h.timestamp,
            h.portfolio_name,
            h.tickers,
            h.weights,
            h.years_back,
            h.rebalance_option,
            m.annualized_return,
            m.max_drawdown
        FROM search_history h
        LEFT JOIN portfolio_metrics m ON h.id = m.search_id
        ORDER BY h.timestamp DESC
    """

    df = pd.read_sql_query(query, conn)
    conn.close()

    # Parse JSON columns
    df['tickers'] = df['tickers'].apply(lambda x: ', '.join(json.loads(x)) if x else '')

    print("\n" + "="*80)
    print("PORTFOLIO SEARCH HISTORY")
    print("="*80)
    print(f"\nTotal searches: {len(df)}\n")
    print(df.to_string(index=False))
    print("\n" + "="*80 + "\n")


def view_statistics():
    """Display database statistics."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Total searches
    cursor.execute("SELECT COUNT(*) FROM search_history")
    total = cursor.fetchone()[0]

    # Searches by portfolio name
    cursor.execute("""
        SELECT portfolio_name, COUNT(*) as count
        FROM search_history
        GROUP BY portfolio_name
        ORDER BY count DESC
    """)
    by_portfolio = cursor.fetchall()

    # Most recent search
    cursor.execute("""
        SELECT timestamp, portfolio_name
        FROM search_history
        ORDER BY timestamp DESC
        LIMIT 1
    """)
    recent = cursor.fetchone()

    conn.close()

    print("\n" + "="*80)
    print("DATABASE STATISTICS")
    print("="*80)
    print(f"\nTotal searches: {total}")
    print(f"\nSearches by portfolio:")
    for name, count in by_portfolio:
        print(f"  - {name}: {count}")
    if recent:
        print(f"\nMost recent search: {recent[1]} at {recent[0]}")
    print("\n" + "="*80 + "\n")


def delete_search(search_id):
    """Delete a specific search by ID."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("DELETE FROM portfolio_metrics WHERE search_id = ?", (search_id,))
    cursor.execute("DELETE FROM search_history WHERE id = ?", (search_id,))

    conn.commit()
    conn.close()

    print(f"\n✓ Deleted search ID: {search_id}\n")


def clear_all():
    """Clear all data from database."""
    response = input("Are you sure you want to clear ALL history? (yes/no): ")
    if response.lower() == 'yes':
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM portfolio_metrics")
        cursor.execute("DELETE FROM search_history")
        conn.commit()
        conn.close()
        print("\n✓ All history cleared!\n")
    else:
        print("\n✗ Cancelled.\n")


def export_to_csv(filename="portfolio_history_export.csv"):
    """Export database to CSV file."""
    conn = sqlite3.connect(DB_PATH)

    query = """
        SELECT
            h.id,
            h.timestamp,
            h.portfolio_name,
            h.tickers,
            h.weights,
            h.years_back,
            h.rebalance_option,
            m.total_return,
            m.annualized_return,
            m.annualized_volatility,
            m.max_drawdown,
            m.period
        FROM search_history h
        LEFT JOIN portfolio_metrics m ON h.id = m.search_id
        ORDER BY h.timestamp DESC
    """

    df = pd.read_sql_query(query, conn)
    conn.close()

    # Parse JSON columns
    df['tickers'] = df['tickers'].apply(lambda x: ', '.join(json.loads(x)) if x else '')
    df['weights'] = df['weights'].apply(lambda x: ', '.join([str(w) for w in json.loads(x)]) if x else '')

    df.to_csv(filename, index=False)
    print(f"\n✓ Exported to {filename}\n")


def main():
    """Main menu."""
    while True:
        print("\n" + "="*50)
        print("Portfolio Database Viewer")
        print("="*50)
        print("1. View all searches")
        print("2. View statistics")
        print("3. Delete a search")
        print("4. Export to CSV")
        print("5. Clear all history")
        print("6. Exit")
        print("="*50)

        choice = input("\nSelect option (1-6): ").strip()

        if choice == '1':
            view_all_searches()
        elif choice == '2':
            view_statistics()
        elif choice == '3':
            search_id = input("Enter search ID to delete: ").strip()
            if search_id.isdigit():
                delete_search(int(search_id))
            else:
                print("\n✗ Invalid ID\n")
        elif choice == '4':
            filename = input("Enter filename (default: portfolio_history_export.csv): ").strip()
            if not filename:
                filename = "portfolio_history_export.csv"
            export_to_csv(filename)
        elif choice == '5':
            clear_all()
        elif choice == '6':
            print("\nGoodbye!\n")
            break
        else:
            print("\n✗ Invalid option\n")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nExiting...\n")
    except Exception as e:
        print(f"\n✗ Error: {e}\n")
