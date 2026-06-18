import sqlite3
from dataclasses import dataclass
from typing import List, Optional, Tuple


@dataclass
class Product:
    """Represents a product in the store."""

    product_id: int
    name: str
    price: float
    quantity: int


class DatabaseConnection:
    """Manages the SQLite database connection."""

    def __init__(self, db_path: str = "store.db"):
        self.db_path = db_path
        self.conn: Optional[sqlite3.Connection] = None
        self.cursor: Optional[sqlite3.Cursor] = None

    def connect(self) -> None:
        try:
            self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
            self.cursor = self.conn.cursor()
            self.cursor.execute("PRAGMA foreign_keys = ON")
            print("Successfully connected to SQLite database.")
        except sqlite3.Error as exc:
            print(f"Connection error: {exc}")
            raise

    def close(self) -> None:
        if self.cursor:
            self.cursor.close()
            self.cursor = None
        if self.conn:
            self.conn.close()
            self.conn = None
            print("Database connection closed.")

    def commit(self) -> None:
        if self.conn:
            self.conn.commit()


class StorageManager:
    """Manages product and inventory operations."""

    def __init__(self, db: DatabaseConnection):
        self.db = db

    def add_product(self, product_id: int, quantity: int) -> None:
        check_query = "SELECT 1 FROM Storage WHERE ProductID = ?"
        self.db.cursor.execute(check_query, (product_id,))
        exists = self.db.cursor.fetchone()

        if exists:
            update_query = "UPDATE Storage SET Quantity = Quantity + ? WHERE ProductID = ?"
            self.db.cursor.execute(update_query, (quantity, product_id))
        else:
            insert_query = "INSERT INTO Storage (ProductID, Quantity) VALUES (?, ?)"
            self.db.cursor.execute(insert_query, (product_id, quantity))

        self.db.commit()
        print(f"Added {quantity} units of ProductID {product_id} to Storage.")

    def get_inventory(self) -> List[Product]:
        query = """
            SELECT p.ProductID, p.ProductName, p.Price, COALESCE(s.Quantity, 0) AS Quantity
            FROM Products p
            LEFT JOIN Storage s ON p.ProductID = s.ProductID
            ORDER BY p.ProductID
        """
        try:
            self.db.cursor.execute(query)
            rows = self.db.cursor.fetchall()
            return [Product(row[0], row[1], row[2], row[3]) for row in rows]
        except sqlite3.Error as exc:
            print(f"Error retrieving inventory: {exc}")
            raise

    def add_new_product(self, name: str, price: float) -> int:
        query = """
            INSERT INTO Products (ProductName, Price, Availability)
            VALUES (?, ?, 1)
        """
        try:
            self.db.cursor.execute(query, (name, price))
            self.db.commit()
            product_id = self.db.cursor.lastrowid
            print(f"Added new product: {name} with ID {product_id}.")
            return int(product_id)
        except sqlite3.Error as exc:
            print(f"Error adding new product: {exc}")
            raise

    def is_product_active(self, product_id: int) -> bool:
        query = "SELECT Availability FROM Products WHERE ProductID = ?"
        self.db.cursor.execute(query, (product_id,))
        row = self.db.cursor.fetchone()
        return bool(row and row[0] == 1)

    def delete_product(self, product_id: int) -> None:
        query = "UPDATE Products SET Availability = 0 WHERE ProductID = ?"
        try:
            self.db.cursor.execute(query, (product_id,))
            self.db.commit()
            print(f"ProductID {product_id} marked as inactive.")
        except sqlite3.Error as exc:
            print(f"Error deactivating product: {exc}")
            raise

    def activate_product(self, product_id: int) -> None:
        query = "UPDATE Products SET Availability = 1 WHERE ProductID = ?"
        try:
            self.db.cursor.execute(query, (product_id,))
            self.db.commit()
            print(f"ProductID {product_id} marked as active.")
        except sqlite3.Error as exc:
            print(f"Error activating product: {exc}")
            raise

    def has_sufficient_quantity(self, product_id: int, quantity: int) -> bool:
        query = "SELECT Quantity FROM Storage WHERE ProductID = ?"
        self.db.cursor.execute(query, (product_id,))
        row = self.db.cursor.fetchone()
        return bool(row and int(row[0]) >= quantity)


class StoreManager:
    """Manages physical store sales."""

    def __init__(self, db: DatabaseConnection):
        self.db = db
        self.storage = StorageManager(db)

    def check_product_exists(self, product_id: int) -> bool:
        query = "SELECT 1 FROM Products WHERE ProductID = ?"
        self.db.cursor.execute(query, (product_id,))
        return self.db.cursor.fetchone() is not None

    def record_sale(self, product_id: int, quantity: int) -> None:
        if quantity <= 0:
            raise ValueError("Quantity must be greater than 0.")

        if not self.storage.is_product_active(product_id):
            raise ValueError(f"Product {product_id} is inactive and cannot be sold.")

        query = "SELECT Quantity FROM Storage WHERE ProductID = ?"
        self.db.cursor.execute(query, (product_id,))
        row = self.db.cursor.fetchone()
        available_quantity = row[0] if row else 0

        if available_quantity < quantity:
            raise ValueError(
                f"Insufficient stock in storage. Requested: {quantity}, Available: {available_quantity}."
            )

        query_insert = "INSERT INTO StoreSales (ProductID, Quantity) VALUES (?, ?)"
        try:
            self.db.cursor.execute(query_insert, (product_id, quantity))
            self.db.commit()
            print(f"Store sale recorded for ProductID {product_id}, Quantity: {quantity}.")
        except sqlite3.Error as exc:
            print(f"Error recording store sale: {exc}")
            raise


class OnlineShopManager:
    """Manages online shop sales."""

    def __init__(self, db: DatabaseConnection):
        self.db = db
        self.storage = StorageManager(db)

    def record_sale(self, product_id: int, quantity: int) -> None:
        if quantity <= 0:
            raise ValueError("Quantity must be greater than 0.")

        if not self.storage.is_product_active(product_id):
            raise ValueError(f"Product {product_id} is inactive and cannot be sold.")

        query = "SELECT Quantity FROM Storage WHERE ProductID = ?"
        self.db.cursor.execute(query, (product_id,))
        row = self.db.cursor.fetchone()
        available_quantity = row[0] if row else 0

        if available_quantity < quantity:
            raise ValueError(
                f"Insufficient stock in storage. Requested: {quantity}, Available: {available_quantity}."
            )

        query_insert = "INSERT INTO OnlineSales (ProductID, Quantity) VALUES (?, ?)"
        try:
            self.db.cursor.execute(query_insert, (product_id, quantity))
            self.db.commit()
            print(f"Online sale recorded for ProductID {product_id}, Quantity: {quantity}.")
        except sqlite3.Error as exc:
            print(f"Error recording online sale: {exc}")
            raise

    def check_product_exists(self, product_id: int) -> bool:
        query = "SELECT 1 FROM Products WHERE ProductID = ?"
        self.db.cursor.execute(query, (product_id,))
        return self.db.cursor.fetchone() is not None


class ReportManager:
    """Manages reporting operations."""

    def __init__(self, db: DatabaseConnection):
        self.db = db

    def get_sales_report(self) -> List[Tuple]:
        query = """
            SELECT
                p.ProductID,
                p.ProductName,
                p.Price,
                COALESCE(s.Quantity, 0) AS StorageQuantity,
                COALESCE((SELECT SUM(ss.Quantity) FROM StoreSales ss WHERE ss.ProductID = p.ProductID), 0) AS StoreSalesQuantity,
                COALESCE((SELECT SUM(os.Quantity) FROM OnlineSales os WHERE os.ProductID = p.ProductID), 0) AS OnlineSalesQuantity,
                COALESCE((SELECT SUM(ss.Quantity) FROM StoreSales ss WHERE ss.ProductID = p.ProductID), 0) +
                COALESCE((SELECT SUM(os.Quantity) FROM OnlineSales os WHERE os.ProductID = p.ProductID), 0) AS TotalSalesQuantity,
                p.Availability
            FROM Products p
            LEFT JOIN Storage s ON p.ProductID = s.ProductID
            ORDER BY p.ProductID
        """
        try:
            self.db.cursor.execute(query)
            return self.db.cursor.fetchall()
        except sqlite3.Error as exc:
            print(f"Error generating sales report: {exc}")
            raise


class StoreApp:
    """Coordinates storage, sales, online shop, and reporting operations."""

    def __init__(self, db_path: str = "store.db"):
        self.db = DatabaseConnection(db_path)
        self.storage = StorageManager(self.db)
        self.store = StoreManager(self.db)
        self.online_shop = OnlineShopManager(self.db)
        self.report = ReportManager(self.db)

    def start(self) -> None:
        self.db.connect()

    def stop(self) -> None:
        self.db.close()

    def get_product_by_id(self, product_id: int) -> Optional[Product]:
        inventory = self.storage.get_inventory()
        for product in inventory:
            if product.product_id == product_id:
                return product
        return None

    def add_product_to_inventory(self, product_id: int, quantity: int) -> None:
        self.storage.add_product(product_id, quantity)

    def add_new_product(self, name: str, price: float) -> int:
        return self.storage.add_new_product(name, price)

    def record_store_sale(self, product_id: int, quantity: int) -> None:
        self.store.record_sale(product_id, quantity)

    def record_online_sale(self, product_id: int, quantity: int) -> None:
        self.online_shop.record_sale(product_id, quantity)

    def display_inventory(self) -> None:
        print("\nCurrent Inventory:")
        for product in self.storage.get_inventory():
            print(
                f"ProductID: {product.product_id}, Name: {product.name}, "
                f"Price: {product.price}, Quantity: {product.quantity}"
            )

    def display_sales_report(self) -> None:
        print("\nSales Report:")
        for row in self.report.get_sales_report():
            status = "Active" if row[7] else "Inactive"
            print(
                f"ProductID: {row[0]}, Name: {row[1]}, Price: {row[2]}, "
                f"Storage: {row[3]}, Store Sales: {row[4]}, Online Sales: {row[5]}, "
                f"Total Sales: {row[6]}, Status: {status}"
            )


if __name__ == "__main__":
    app = StoreApp("store.db")
    try:
        app.start()
        app.display_inventory()
        app.display_sales_report()
    finally:
        app.stop()
