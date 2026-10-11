"""
Turso (libsql) Database Connection and DMart Ingestion Manager.
Provides production-grade connection management for Turso serverless databases
and local SQLite/libsql embedded databases with automated schema mapping and CSV ingestion.
"""

import os
import glob
import logging
import sqlite3
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
import pandas as pd
import numpy as np
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger("upiai.database")

# Environment configuration
TURSO_DATABASE_URL = os.getenv("TURSO_DATABASE_URL", "file:upiai_turso.db")
TURSO_AUTH_TOKEN = os.getenv("TURSO_AUTH_TOKEN", "")
DATABASE_NAME = os.getenv("DATABASE_NAME", "upiai_turso_db")

# Optional libsql_client import for remote Turso sync/async connections
try:
    import libsql_client
    LIBSQL_AVAILABLE = True
except ImportError:
    LIBSQL_AVAILABLE = False


class TursoDatabaseManager:
    """
    Manages Turso (libsql) connection, local SQLite fallback,
    and automatic ingestion of real DMart retail datasets.
    """

    def __init__(self):
        self.db_url: str = TURSO_DATABASE_URL
        self.auth_token: str = TURSO_AUTH_TOKEN
        self.is_connected: bool = False
        self.is_remote_turso: bool = False
        self.local_db_path: str = "upiai_turso.db"
        self._sync_conn: Optional[sqlite3.Connection] = None
        self._libsql_client = None

    def _get_sqlite_path(self) -> str:
        """Resolves file path for local SQLite storage relative to root workspace."""
        if self.db_url.startswith("file:"):
            path = self.db_url.replace("file:", "")
        elif self.db_url.endswith(".db"):
            path = self.db_url
        else:
            path = self.local_db_path
        if not os.path.isabs(path):
            root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
            path = os.path.join(root_dir, path)
        return path

    def ensure_initialized(self):
        """Synchronously ensures database schema and tables exist."""
        if not self.is_connected:
            try:
                db_file = self._get_sqlite_path()
                self._sync_conn = self.get_connection(skip_init=True)
                self.is_connected = True
                self.is_remote_turso = False
                self._create_tables()
                self._ingest_dmart_datasets()
            except Exception as exc:
                logger.error("[ERROR] Failed to synchronously initialize database: %s", exc)

    def get_connection(self, skip_init: bool = False) -> sqlite3.Connection:
        """Returns a synchronized thread-safe database connection with WAL mode."""
        if not skip_init and not self.is_connected:
            self.ensure_initialized()
        db_file = self._get_sqlite_path()
        conn = sqlite3.connect(db_file, check_same_thread=False, timeout=20.0)
        try:
            conn.execute("PRAGMA journal_mode=WAL;")
            conn.execute("PRAGMA busy_timeout=5000;")
        except Exception:
            pass
        conn.row_factory = sqlite3.Row
        return conn

    async def connect_db(self):
        """Initializes database schema and triggers DMart CSV auto-ingestion."""
        logger.info("Initializing Turso / libsql database connection (%s)...", self.db_url)
        try:
            if self.db_url.startswith("libsql://") and LIBSQL_AVAILABLE and self.auth_token:
                self._libsql_client = libsql_client.create_client_sync(
                    url=self.db_url,
                    auth_token=self.auth_token
                )
                self.is_remote_turso = True
                self.is_connected = True
                logger.info("[OK] Connected to Remote Turso Database at %s", self.db_url)
            else:
                db_file = self._get_sqlite_path()
                self._sync_conn = self.get_connection(skip_init=True)
                self.is_connected = True
                self.is_remote_turso = False
                logger.info("[OK] Connected to Turso-compatible local database engine (%s)", db_file)

            # Initialize schema & ingest DMart data
            self._create_tables()
            self._ingest_dmart_datasets()
        except Exception as exc:
            logger.error("[ERROR] Failed to initialize database: %s. Using in-memory fallback.", exc)
            self.is_connected = False

    def _create_tables(self):
        """Creates canonical tables for DMart transactions, categories, inventory, and suppliers."""
        conn = self.get_connection()
        cursor = conn.cursor()

        # 1. DMart Transactions Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS dmart_transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                transaction_date TEXT NOT NULL,
                transaction_time TEXT NOT NULL,
                transaction_datetime TEXT NOT NULL,
                customer_type TEXT NOT NULL,
                product_category TEXT NOT NULL,
                unit_price REAL NOT NULL,
                units_sold INTEGER NOT NULL,
                total_amount REAL NOT NULL,
                customer_name TEXT NOT NULL,
                estimated_cost REAL NOT NULL,
                gross_profit REAL NOT NULL,
                margin_pct REAL NOT NULL,
                source_file TEXT NOT NULL
            )
        """)

        # 2. Categories Performance Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS dmart_categories (
                category TEXT PRIMARY KEY,
                total_revenue REAL NOT NULL,
                total_units INTEGER NOT NULL,
                avg_price REAL NOT NULL,
                avg_margin_pct REAL NOT NULL,
                transaction_count INTEGER NOT NULL
            )
        """)

        # 3. Inventory State Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS dmart_inventory (
                sku TEXT PRIMARY KEY,
                product_name TEXT NOT NULL,
                category TEXT NOT NULL,
                current_stock INTEGER NOT NULL,
                unit_cost REAL NOT NULL,
                unit_price REAL NOT NULL,
                reorder_point INTEGER NOT NULL,
                safety_stock INTEGER NOT NULL,
                lead_time_days INTEGER NOT NULL,
                supplier_id TEXT NOT NULL
            )
        """)

        # 4. Suppliers Ledger Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS dmart_suppliers (
                supplier_id TEXT PRIMARY KEY,
                supplier_name TEXT NOT NULL,
                category TEXT NOT NULL,
                avg_lead_time_days INTEGER NOT NULL,
                on_time_delivery_rate REAL NOT NULL,
                quality_rating REAL NOT NULL,
                payment_terms TEXT NOT NULL,
                balance_due REAL NOT NULL,
                payment_status TEXT NOT NULL,
                contact_email TEXT NOT NULL
            )
        """)

        # Create indexes for fast querying
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_txn_date ON dmart_transactions(transaction_date);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_txn_category ON dmart_transactions(product_category);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_txn_cust_type ON dmart_transactions(customer_type);")
        conn.commit()
        conn.close()
        logger.info("Turso database tables and indexes verified.")

    def _find_dmart_csv_files(self) -> List[str]:
        """Discovers DMart raw CSV datasets from standard workspace locations."""
        root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
        possible_paths = [
            "C:/dataset/DMart_sample_data.csv",
            "C:\\dataset\\DMart_sample_data.csv",
            os.path.join(root_dir, "data", "processed", "DMart_cleaned_sample_10k.csv"),
            os.path.join(root_dir, "data", "raw", "DMart_sample_data.csv"),
            os.path.join(root_dir, "data", "raw", "DMart_Grocery_Sales_-_Retail_Analytics_Dataset.csv"),
            os.path.join(root_dir, "data", "DMart_sample_data.csv"),
            os.path.join(root_dir, "data", "DMart_Grocery_Sales_-_Retail_Analytics_Dataset.csv"),
            "data/raw/DMart_sample_data.csv",
            "data/raw/DMart_Grocery_Sales_-_Retail_Analytics_Dataset.csv",
            "../data/raw/DMart_sample_data.csv",
            "../data/raw/DMart_Grocery_Sales_-_Retail_Analytics_Dataset.csv",
        ]
        found = []
        for p in possible_paths:
            norm = os.path.abspath(p)
            if os.path.exists(norm) and norm not in found:
                found.append(norm)

        # Also glob data/raw if available
        glob_paths = glob.glob("**/data/raw/*.csv", recursive=True) + glob.glob("data/raw/*.csv")
        for g in glob_paths:
            norm = os.path.abspath(g)
            if os.path.exists(norm) and norm not in found:
                found.append(norm)

        return found

    def _ingest_dmart_datasets(self):
        """Maps columns and ingests DMart datasets into Turso tables."""
        conn = self.get_connection()
        cursor = conn.cursor()

        # Check existing transaction count
        cursor.execute("SELECT COUNT(*) FROM dmart_transactions")
        count = cursor.fetchone()[0]
        if count > 0:
            logger.info("DMart transactions already populated (%d records found).", count)
            conn.close()
            return

        csv_files = self._find_dmart_csv_files()
        if not csv_files:
            logger.warning("No DMart CSV datasets discovered. Creating sample seeded DMart records.")
            self._seed_sample_dmart_data(conn)
            conn.close()
            return

        total_inserted = 0
        for file_path in csv_files:
            file_name = os.path.basename(file_path)
            logger.info("Ingesting DMart dataset: %s", file_name)
            try:
                df = pd.read_csv(file_path)
                if df.empty:
                    continue

                # Schema mapping
                col_map = {}
                for c in df.columns:
                    clow = c.strip().lower()
                    if clow in ["date", "transaction_date", "order_date", "day"]:
                        col_map[c] = "Date"
                    elif clow in ["time", "transaction_time", "hour"]:
                        col_map[c] = "Time"
                    elif clow in ["customertype", "customer_type", "type", "member_type"]:
                        col_map[c] = "CustomerType"
                    elif clow in ["productcategory", "product_category", "category", "dept"]:
                        col_map[c] = "ProductCategory"
                    elif clow in ["unitprice", "unit_price", "price", "rate"]:
                        col_map[c] = "UnitPrice"
                    elif clow in ["quantity", "units_sold", "qty", "volume"]:
                        col_map[c] = "Quantity"
                    elif clow in ["total", "total_amount", "amount", "revenue"]:
                        col_map[c] = "Total"
                    elif clow in ["fullname", "customer_name", "name", "client"]:
                        col_map[c] = "FullName"

                df = df.rename(columns=col_map)

                # Ensure defaults for missing canonical columns
                if "Date" not in df.columns:
                    df["Date"] = datetime.utcnow().strftime("%Y-%m-%d")
                if "Time" not in df.columns:
                    df["Time"] = "12:00:00"
                if "CustomerType" not in df.columns:
                    df["CustomerType"] = "Regular"
                if "ProductCategory" not in df.columns:
                    df["ProductCategory"] = "Grocery & Staples"
                if "UnitPrice" not in df.columns:
                    df["UnitPrice"] = 100.0
                if "Quantity" not in df.columns:
                    df["Quantity"] = 1
                if "Total" not in df.columns:
                    df["Total"] = df["UnitPrice"] * df["Quantity"]
                if "FullName" not in df.columns:
                    df["FullName"] = "Customer"

                # Clean and parse types
                df["Date"] = pd.to_datetime(df["Date"], errors='coerce').dt.strftime('%Y-%m-%d').fillna("2026-06-01")
                df["Time"] = df["Time"].astype(str)
                df["UnitPrice"] = pd.to_numeric(df["UnitPrice"], errors='coerce').fillna(100.0)
                df["Quantity"] = pd.to_numeric(df["Quantity"], errors='coerce').fillna(1).astype(int)
                df["Total"] = pd.to_numeric(df["Total"], errors='coerce').fillna(df["UnitPrice"] * df["Quantity"])
                df["ProductCategory"] = df["ProductCategory"].astype(str).str.strip()
                df["CustomerType"] = df["CustomerType"].astype(str).str.strip()
                df["FullName"] = df["FullName"].astype(str).str.strip()

                # Estimated cost (70% COGS -> 30% gross profit margin standard in Indian retail)
                df["EstimatedCost"] = df["UnitPrice"] * 0.70
                df["GrossProfit"] = df["Total"] - (df["EstimatedCost"] * df["Quantity"])
                df["MarginPct"] = np.where(df["Total"] > 0, (df["GrossProfit"] / df["Total"]) * 100.0, 30.0)

                for _, row in df.iterrows():
                    txn_dt = f"{row['Date']} {row['Time']}"
                    cursor.execute("""
                        INSERT INTO dmart_transactions (
                            transaction_date, transaction_time, transaction_datetime,
                            customer_type, product_category, unit_price, units_sold,
                            total_amount, customer_name, estimated_cost, gross_profit,
                            margin_pct, source_file
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        row['Date'], row['Time'], txn_dt,
                        row['CustomerType'], row['ProductCategory'], float(row['UnitPrice']),
                        int(row['Quantity']), float(row['Total']), row['FullName'],
                        float(row['EstimatedCost']), float(row['GrossProfit']),
                        float(row['MarginPct']), file_name
                    ))
                    total_inserted += 1

            except Exception as err:
                logger.error("Error reading DMart CSV %s: %s", file_name, err)

        conn.commit()
        logger.info("[OK] Ingested %d total DMart transaction records into Turso.", total_inserted)

        # Aggregate category analytics and populate secondary inventory/supplier tables
        self._populate_category_summaries(conn)
        self._populate_inventory_and_suppliers(conn)
        conn.close()

    def _seed_sample_dmart_data(self, conn: sqlite3.Connection):
        """Generates initial realistic DMart records if CSV files are absent."""
        cursor = conn.cursor()
        sample_rows = [
            ("2026-06-01", "10:15:22", "Member", "Grocery & Staples", 120.0, 3, 360.0, "Aarav Sharma"),
            ("2026-06-01", "11:05:10", "Corporate", "Beverages", 45.0, 10, 450.0, "Rohan Gupta"),
            ("2026-06-01", "11:42:30", "Member", "Dairy & Eggs", 60.0, 4, 240.0, "Ananya Iyer"),
            ("2026-06-01", "12:15:18", "Regular", "Snacks & Confectionery", 35.0, 5, 175.0, "Vikram Malhotra"),
            ("2026-06-01", "13:00:55", "Member", "Home & Cleaning", 150.0, 2, 300.0, "Sneha Kulkarni"),
            ("2026-06-02", "14:15:50", "Corporate", "Grocery & Staples", 450.0, 4, 1800.0, "Deepak Chawla"),
            ("2026-06-02", "15:30:22", "Member", "Personal Care", 140.0, 2, 280.0, "Ritu Saxena"),
            ("2026-06-02", "16:45:10", "Regular", "Snacks & Confectionery", 75.0, 3, 225.0, "Nikhil Sen"),
            ("2026-06-03", "10:00:15", "Regular", "Grocery & Staples", 80.0, 4, 320.0, "Arjun Mehta"),
            ("2026-06-03", "10:50:30", "Member", "Beverages", 65.0, 4, 260.0, "Kavita Singhania")
        ]
        for r in sample_rows:
            cost = r[4] * 0.70
            profit = r[6] - (cost * r[5])
            margin = (profit / r[6]) * 100.0
            cursor.execute("""
                INSERT INTO dmart_transactions (
                    transaction_date, transaction_time, transaction_datetime,
                    customer_type, product_category, unit_price, units_sold,
                    total_amount, customer_name, estimated_cost, gross_profit,
                    margin_pct, source_file
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                r[0], r[1], f"{r[0]} {r[1]}", r[2], r[3], r[4], r[5], r[6], r[7],
                cost, profit, margin, "DMart_synthetic_seed"
            ))
        conn.commit()
        self._populate_category_summaries(conn)
        self._populate_inventory_and_suppliers(conn)

    def _populate_category_summaries(self, conn: sqlite3.Connection):
        """Aggregates transactional sales by DMart product category."""
        cursor = conn.cursor()
        cursor.execute("DELETE FROM dmart_categories")
        cursor.execute("""
            INSERT INTO dmart_categories (
                category, total_revenue, total_units, avg_price, avg_margin_pct, transaction_count
            )
            SELECT 
                product_category,
                ROUND(SUM(total_amount), 2) as total_revenue,
                SUM(units_sold) as total_units,
                ROUND(AVG(unit_price), 2) as avg_price,
                ROUND(AVG(margin_pct), 2) as avg_margin_pct,
                COUNT(*) as transaction_count
            FROM dmart_transactions
            GROUP BY product_category
        """)
        conn.commit()

    def _populate_inventory_and_suppliers(self, conn: sqlite3.Connection):
        """Derives inventory items and supplier performance profiles from DMart categories."""
        cursor = conn.cursor()
        cursor.execute("DELETE FROM dmart_inventory")
        cursor.execute("DELETE FROM dmart_suppliers")

        # Query categories
        cursor.execute("SELECT category, avg_price, total_units FROM dmart_categories")
        categories = cursor.fetchall()

        suppliers_data = [
            ("SUP-DMART-01", "Hindustan Unilever Distribution", "Personal Care", 7, 0.96, 4.8, "Net 30", 45000.0, "Paid", "supply@hul-dist.in"),
            ("SUP-DMART-02", "ITC Agri-Business Division", "Grocery & Staples", 10, 0.92, 4.6, "Net 45", 82000.0, "Pending", "orders@itc-agri.in"),
            ("SUP-DMART-03", "Amul Dairy Cooperatives", "Dairy & Eggs", 3, 0.98, 4.9, "Net 15", 28000.0, "Paid", "dispatch@amuldairy.in"),
            ("SUP-DMART-04", "Britannia & Parle Logistics", "Snacks & Confectionery", 5, 0.94, 4.5, "Net 30", 31000.0, "Paid", "fulfillment@britannia-hub.in"),
            ("SUP-DMART-05", "Tata Consumer & Beverages", "Beverages", 6, 0.95, 4.7, "Net 30", 19500.0, "Paid", "beverages@tataconsumer.in"),
            ("SUP-DMART-06", "Godrej Consumer Products", "Home & Cleaning", 8, 0.89, 4.2, "Net 45", 54000.0, "Overdue", "b2b@godrejcp.in")
        ]

        for sup in suppliers_data:
            cursor.execute("""
                INSERT OR REPLACE INTO dmart_suppliers (
                    supplier_id, supplier_name, category, avg_lead_time_days,
                    on_time_delivery_rate, quality_rating, payment_terms,
                    balance_due, payment_status, contact_email
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, sup)

        sku_idx = 1
        for cat_row in categories:
            cat = cat_row["category"]
            avg_price = float(cat_row["avg_price"])
            cost = round(avg_price * 0.70, 2)
            sku = f"DMART-{cat[:3].upper()}-{sku_idx:03d}"
            sku_idx += 1

            # Match supplier
            sup_id = "SUP-DMART-01"
            for s in suppliers_data:
                if s[2].lower() in cat.lower() or cat.lower() in s[2].lower():
                    sup_id = s[0]
                    break

            cursor.execute("""
                INSERT OR REPLACE INTO dmart_inventory (
                    sku, product_name, category, current_stock, unit_cost,
                    unit_price, reorder_point, safety_stock, lead_time_days, supplier_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                sku, f"DMart Essential {cat}", cat, 140, cost,
                avg_price, 45, 20, 7, sup_id
            ))

        conn.commit()

    # -----------------------------------------------------------------------
    # Query APIs for FastAPI and ML Routers
    # -----------------------------------------------------------------------

    def get_kpis(self) -> Dict[str, Any]:
        """Calculates executive KPI metrics across all DMart records."""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT 
                COUNT(*) as total_transactions,
                COALESCE(SUM(units_sold), 0) as total_units_sold,
                COALESCE(SUM(total_amount), 0.0) as total_revenue,
                COALESCE(SUM(gross_profit), 0.0) as total_profit,
                COALESCE(AVG(total_amount), 0.0) as avg_order_value,
                COALESCE(AVG(margin_pct), 30.0) as avg_margin_pct,
                COUNT(DISTINCT product_category) as total_categories,
                COUNT(DISTINCT customer_name) as unique_customers
            FROM dmart_transactions
        """)
        row = cursor.fetchone()
        conn.close()

        if not row:
            return {
                "total_transactions": 0,
                "total_units_sold": 0,
                "total_revenue": 0.0,
                "total_profit": 0.0,
                "avg_order_value": 0.0,
                "avg_margin_pct": 0.0,
                "total_categories": 0,
                "unique_customers": 0
            }

        return {
            "total_transactions": int(row["total_transactions"]),
            "total_units_sold": int(row["total_units_sold"]),
            "total_revenue": round(float(row["total_revenue"]), 2),
            "total_profit": round(float(row["total_profit"]), 2),
            "avg_order_value": round(float(row["avg_order_value"]), 2),
            "avg_margin_pct": round(float(row["avg_margin_pct"]), 2),
            "total_categories": int(row["total_categories"]),
            "unique_customers": int(row["unique_customers"])
        }

    def get_all_transactions(self, limit: int = 500, category: Optional[str] = None) -> List[Dict[str, Any]]:
        """Retrieves individual DMart transaction line items."""
        conn = self.get_connection()
        cursor = conn.cursor()
        if category:
            cursor.execute(
                "SELECT * FROM dmart_transactions WHERE product_category = ? ORDER BY transaction_date DESC, id DESC LIMIT ?",
                (category, limit)
            )
        else:
            cursor.execute("SELECT * FROM dmart_transactions ORDER BY transaction_date DESC, id DESC LIMIT ?", (limit,))
        rows = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return rows

    def get_category_summary(self) -> List[Dict[str, Any]]:
        """Retrieves aggregated sales and margins per category."""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM dmart_categories ORDER BY total_revenue DESC")
        rows = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return rows

    def get_daily_sales_series(self, category: Optional[str] = None) -> pd.DataFrame:
        """Retrieves continuous daily sales time-series for ML feature engineering."""
        conn = self.get_connection()
        if category:
            query = """
                SELECT transaction_date as date, SUM(units_sold) as units_sold, SUM(total_amount) as revenue
                FROM dmart_transactions
                WHERE product_category = ?
                GROUP BY transaction_date
                ORDER BY transaction_date ASC
            """
            df = pd.read_sql_query(query, conn, params=(category,))
        else:
            query = """
                SELECT transaction_date as date, SUM(units_sold) as units_sold, SUM(total_amount) as revenue
                FROM dmart_transactions
                GROUP BY transaction_date
                ORDER BY transaction_date ASC
            """
            df = pd.read_sql_query(query, conn)
        conn.close()
        return df

    def get_customer_type_distribution(self) -> List[Dict[str, Any]]:
        """Analyzes sales performance grouped by customer tier (Member, Regular, Corporate)."""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT 
                customer_type,
                COUNT(*) as transaction_count,
                SUM(units_sold) as total_units,
                ROUND(SUM(total_amount), 2) as total_revenue,
                ROUND(AVG(total_amount), 2) as avg_basket_size
            FROM dmart_transactions
            GROUP BY customer_type
            ORDER BY total_revenue DESC
        """)
        rows = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return rows

    def get_hourly_traffic(self) -> List[Dict[str, Any]]:
        """Calculates store velocity by hour of day."""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT 
                SUBSTR(transaction_time, 1, 2) || ':00' as hour_window,
                COUNT(*) as transaction_count,
                SUM(units_sold) as total_units,
                ROUND(SUM(total_amount), 2) as total_revenue
            FROM dmart_transactions
            GROUP BY hour_window
            ORDER BY hour_window ASC
        """)
        rows = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return rows

    def get_inventory_items(self) -> List[Dict[str, Any]]:
        """Returns inventory stock levels, reorder points, and suppliers."""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM dmart_inventory ORDER BY current_stock ASC")
        rows = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return rows

    def get_suppliers(self) -> List[Dict[str, Any]]:
        """Returns vendor performance scorecards and financial ledger balances."""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM dmart_suppliers ORDER BY balance_due DESC")
        rows = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return rows

    def settle_supplier_invoice(self, supplier_id: str) -> bool:
        """Updates supplier invoice status to Paid and zeros balance due."""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE dmart_suppliers
            SET balance_due = 0.0, payment_status = 'Paid'
            WHERE supplier_id = ?
        """, (supplier_id,))
        success = cursor.rowcount > 0
        conn.commit()
        conn.close()
        return success

    def get_db_status(self) -> Dict[str, Any]:
        """Returns connection health and backend storage details."""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM dmart_transactions")
        txn_count = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM dmart_categories")
        cat_count = cursor.fetchone()[0]
        conn.close()

        engine_name = "Turso Remote (libsql)" if self.is_remote_turso else "Turso Local Engine (libsql/SQLite)"
        return {
            "status": "healthy" if self.is_connected else "degraded",
            "connected": self.is_connected,
            "engine": engine_name,
            "database_name": DATABASE_NAME,
            "total_transactions": txn_count,
            "total_categories": cat_count,
            "url_target": self.db_url.split("@")[-1] if "@" in self.db_url else self.db_url
        }


# Global database singleton
turso_db = TursoDatabaseManager()

def get_database_manager() -> TursoDatabaseManager:
    """Dependency provider for Turso database manager."""
    return turso_db
