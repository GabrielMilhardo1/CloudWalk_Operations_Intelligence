"""
Database Module - CloudWalk Operations Intelligence

This module handles SQLite database operations:
- Load CSV data into SQLite
- Provide database connection
- Execute queries
- Common data retrieval functions

Author: Gabriel Milhardo
"""

import sqlite3
import pandas as pd
from pathlib import Path
from typing import Optional, Union
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class Database:
    """
    SQLite database handler for CloudWalk transaction data.

    Attributes:
        db_path: Path to SQLite database file
        csv_path: Path to source CSV file
        table_name: Name of the main transactions table
    """

    def __init__(
        self,
        db_path: str = "cloudwalk.db",
        csv_path: str = "Operations_analyst_data.csv",
        table_name: str = "transactions"
    ):
        """
        Initialize database connection.

        Args:
            db_path: Path to SQLite database file
            csv_path: Path to source CSV file
            table_name: Name for the transactions table
        """
        self.db_path = Path(db_path)
        self.csv_path = Path(csv_path)
        self.table_name = table_name
        self._connection: Optional[sqlite3.Connection] = None

    def connect(self) -> sqlite3.Connection:
        """
        Get or create database connection.

        Returns:
            SQLite connection object
        """
        if self._connection is None:
            self._connection = sqlite3.connect(
                str(self.db_path),
                check_same_thread=False
            )
            logger.info(f"Connected to database: {self.db_path}")
        return self._connection

    def close(self) -> None:
        """Close database connection."""
        if self._connection:
            self._connection.close()
            self._connection = None
            logger.info("Database connection closed")

    def load_csv_to_db(self, if_exists: str = "replace") -> int:
        """
        Load CSV data into SQLite database.

        Args:
            if_exists: How to handle existing table ('replace', 'append', 'fail')

        Returns:
            Number of rows loaded
        """
        logger.info(f"Loading CSV from: {self.csv_path}")

        # Read CSV
        df = pd.read_csv(self.csv_path)

        # Convert day to proper date format
        df['day'] = pd.to_datetime(df['day']).dt.strftime('%Y-%m-%d')

        # Load to SQLite
        conn = self.connect()
        df.to_sql(self.table_name, conn, if_exists=if_exists, index=False)

        # Create index on day column for faster queries
        conn.execute(f"CREATE INDEX IF NOT EXISTS idx_day ON {self.table_name}(day)")
        conn.commit()

        rows_loaded = len(df)
        logger.info(f"Loaded {rows_loaded:,} rows into table '{self.table_name}'")

        return rows_loaded

    def execute_query(self, query: str) -> pd.DataFrame:
        """
        Execute SQL query and return results as DataFrame.

        Args:
            query: SQL query string

        Returns:
            Query results as pandas DataFrame
        """
        conn = self.connect()
        try:
            result = pd.read_sql_query(query, conn)
            logger.debug(f"Query executed successfully: {query[:100]}...")
            return result
        except Exception as e:
            logger.error(f"Query failed: {e}")
            raise

    def get_schema(self) -> str:
        """
        Get database schema as formatted string.

        Returns:
            Schema description for LLM system prompt
        """
        conn = self.connect()
        cursor = conn.execute(f"PRAGMA table_info({self.table_name})")
        columns = cursor.fetchall()

        schema = f"Table: {self.table_name}\n"
        schema += "-" * 50 + "\n"

        for col in columns:
            col_name = col[1]
            col_type = col[2]
            schema += f"- {col_name} ({col_type})\n"

        return schema

    def get_date_range(self) -> tuple:
        """
        Get min and max dates in the dataset.

        Returns:
            Tuple of (min_date, max_date)
        """
        query = f"""
        SELECT MIN(day) as min_date, MAX(day) as max_date
        FROM {self.table_name}
        """
        result = self.execute_query(query)
        return result['min_date'].iloc[0], result['max_date'].iloc[0]

    def get_total_tpv(self) -> float:
        """
        Get total TPV (Total Payment Volume).

        Returns:
            Total TPV as float
        """
        query = f"""
        SELECT SUM(amount_transacted) as total_tpv
        FROM {self.table_name}
        """
        result = self.execute_query(query)
        return result['total_tpv'].iloc[0]

    def get_daily_metrics(self) -> pd.DataFrame:
        """
        Get daily aggregated metrics.

        Returns:
            DataFrame with daily TPV, transactions, and merchants
        """
        query = f"""
        SELECT
            day,
            SUM(amount_transacted) as tpv,
            SUM(quantity_transactions) as transactions,
            SUM(quantity_of_merchants) as merchants
        FROM {self.table_name}
        GROUP BY day
        ORDER BY day
        """
        return self.execute_query(query)

    def get_tpv_by_product(self) -> pd.DataFrame:
        """
        Get TPV breakdown by product.

        Returns:
            DataFrame with TPV per product
        """
        query = f"""
        SELECT
            product,
            SUM(amount_transacted) as tpv,
            SUM(quantity_transactions) as transactions,
            ROUND(SUM(amount_transacted) / SUM(quantity_transactions), 2) as avg_ticket
        FROM {self.table_name}
        GROUP BY product
        ORDER BY tpv DESC
        """
        return self.execute_query(query)

    def get_unique_values(self, column: str) -> list:
        """
        Get unique values for a column.

        Args:
            column: Column name

        Returns:
            List of unique values
        """
        query = f"SELECT DISTINCT {column} FROM {self.table_name}"
        result = self.execute_query(query)
        return result[column].tolist()


# Convenience function for quick setup
def setup_database(
    csv_path: str = "Operations_analyst_data.csv",
    db_path: str = "cloudwalk.db"
) -> Database:
    """
    Quick setup: Create database and load data.

    Args:
        csv_path: Path to CSV file
        db_path: Path for SQLite database

    Returns:
        Configured Database instance
    """
    db = Database(db_path=db_path, csv_path=csv_path)
    db.load_csv_to_db()
    return db


# For direct testing
if __name__ == "__main__":
    print("=" * 60)
    print("DATABASE MODULE TEST")
    print("=" * 60)

    # Setup database
    db = setup_database()

    # Test queries
    print("\n1. Schema:")
    print(db.get_schema())

    print("\n2. Date Range:")
    min_date, max_date = db.get_date_range()
    print(f"   {min_date} to {max_date}")

    print("\n3. Total TPV:")
    total_tpv = db.get_total_tpv()
    print(f"   R$ {total_tpv:,.2f}")

    print("\n4. TPV by Product:")
    print(db.get_tpv_by_product().to_string())

    print("\n5. Sample Query:")
    sample = db.execute_query("""
        SELECT day, SUM(amount_transacted) as tpv
        FROM transactions
        GROUP BY day
        ORDER BY day DESC
        LIMIT 5
    """)
    print(sample.to_string())

    # Close connection
    db.close()
    print("\n[OK] All tests passed!")
