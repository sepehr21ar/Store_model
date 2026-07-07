import psycopg
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
    """Manages the PostgreSQL database connection."""

    def __init__(self, database_url: str):
        self.database_url = database_url
        self.conn: Optional[psycopg.Connection] = None
        self.cursor: Optional[psycopg.Cursor] = None

    def connect(self) -> None:
        try:
            self.conn = psycopg.connect(self.database_url)
            self.cursor = self.conn.cursor()
            print("Successfully connected to PostgreSQL database.")
        except psycopg.Error as exc:
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
        query = """
            INSERT INTO storage (product_id, quantity)
            VALUES (%s, %s)
            ON CONFLICT (product_id)
            DO UPDATE SET quantity = storage.quantity + EXCLUDED.quantity
        """
        self.db.cursor.execute(query, (product_id, quantity))

        self.db.commit()
        print(f"Added {quantity} units of ProductID {product_id} to Storage.")

    def get_inventory(self) -> List[Product]:
        query = """
            SELECT p.product_id, p.product_name, p.price, COALESCE(s.quantity, 0) AS quantity
            FROM products p
            LEFT JOIN storage s ON p.product_id = s.product_id
            ORDER BY p.product_id
        """
        try:
            self.db.cursor.execute(query)
            rows = self.db.cursor.fetchall()
            return [Product(row[0], row[1], row[2], row[3]) for row in rows]
        except psycopg.Error as exc:
            print(f"Error retrieving inventory: {exc}")
            raise

    def add_new_product(self, name: str, price: float) -> int:
        query = """
            INSERT INTO products (product_name, price, availability)
            VALUES (%s, %s, TRUE)
            RETURNING product_id
        """
        try:
            self.db.cursor.execute(query, (name, price))
            product_id = self.db.cursor.fetchone()[0]
            self.db.commit()
            print(f"Added new product: {name} with ID {product_id}.")
            return int(product_id)
        except psycopg.Error as exc:
            print(f"Error adding new product: {exc}")
            raise

    def update_product(self, product_id: int, name: str, price: float) -> None:
        query = """
            UPDATE products
            SET product_name = %s, price = %s
            WHERE product_id = %s
        """
        try:
            self.db.cursor.execute(query, (name, price, product_id))
            self.db.commit()
            print(f"Updated ProductID {product_id}.")
        except psycopg.Error as exc:
            print(f"Error updating product: {exc}")
            raise

    def is_product_active(self, product_id: int) -> bool:
        query = "SELECT availability FROM products WHERE product_id = %s"
        self.db.cursor.execute(query, (product_id,))
        row = self.db.cursor.fetchone()
        return bool(row and row[0])

    def delete_product(self, product_id: int) -> None:
        query = "UPDATE products SET availability = FALSE WHERE product_id = %s"
        try:
            self.db.cursor.execute(query, (product_id,))
            self.db.commit()
            print(f"ProductID {product_id} marked as inactive.")
        except psycopg.Error as exc:
            print(f"Error deactivating product: {exc}")
            raise

    def hard_delete_product(self, product_id: int) -> None:
        try:
            self.db.cursor.execute("DELETE FROM products WHERE product_id = %s", (product_id,))
            self._resequence_product_ids()
            self.db.commit()
            print(f"ProductID {product_id} permanently deleted and product IDs resequenced.")
        except psycopg.Error as exc:
            if self.db.conn:
                self.db.conn.rollback()
            print(f"Error deleting product: {exc}")
            raise

    def _resequence_product_ids(self) -> None:
        self.db.cursor.execute(
            """
            CREATE TEMP TABLE product_id_resequence (
                old_id INTEGER PRIMARY KEY,
                new_id INTEGER NOT NULL
            ) ON COMMIT DROP
            """
        )
        self.db.cursor.execute(
            """
            INSERT INTO product_id_resequence (old_id, new_id)
            SELECT product_id, ROW_NUMBER() OVER (ORDER BY product_id)
            FROM products
            """
        )
        self.db.cursor.execute(
            """
            UPDATE products p
            SET product_id = m.new_id + 1000000
            FROM product_id_resequence m
            WHERE p.product_id = m.old_id
              AND m.old_id <> m.new_id
            """
        )
        self.db.cursor.execute(
            """
            UPDATE products p
            SET product_id = m.new_id
            FROM product_id_resequence m
            WHERE p.product_id = m.new_id + 1000000
              AND m.old_id <> m.new_id
            """
        )
        self.db.cursor.execute("DROP TABLE product_id_resequence")
        self.db.cursor.execute(
            """
            SELECT setval(
                pg_get_serial_sequence('products', 'product_id'),
                COALESCE((SELECT MAX(product_id) FROM products), 1),
                EXISTS (SELECT 1 FROM products)
            )
            """
        )

    def activate_product(self, product_id: int) -> None:
        query = "UPDATE products SET availability = TRUE WHERE product_id = %s"
        try:
            self.db.cursor.execute(query, (product_id,))
            self.db.commit()
            print(f"ProductID {product_id} marked as active.")
        except psycopg.Error as exc:
            print(f"Error activating product: {exc}")
            raise

    def has_sufficient_quantity(self, product_id: int, quantity: int) -> bool:
        query = "SELECT quantity FROM storage WHERE product_id = %s"
        self.db.cursor.execute(query, (product_id,))
        row = self.db.cursor.fetchone()
        return bool(row and int(row[0]) >= quantity)

    def set_inventory_quantity(self, product_id: int, quantity: int) -> None:
        try:
            if quantity == 0:
                self.db.cursor.execute("DELETE FROM storage WHERE product_id = %s", (product_id,))
            else:
                query = """
                    INSERT INTO storage (product_id, quantity)
                    VALUES (%s, %s)
                    ON CONFLICT (product_id)
                    DO UPDATE SET quantity = EXCLUDED.quantity
                """
                self.db.cursor.execute(query, (product_id, quantity))
            self.db.commit()
            print(f"Set ProductID {product_id} inventory to {quantity}.")
        except psycopg.Error as exc:
            print(f"Error setting inventory quantity: {exc}")
            raise


class StoreManager:
    """Manages physical store sales."""

    def __init__(self, db: DatabaseConnection):
        self.db = db
        self.storage = StorageManager(db)

    def check_product_exists(self, product_id: int) -> bool:
        query = "SELECT 1 FROM products WHERE product_id = %s"
        self.db.cursor.execute(query, (product_id,))
        return self.db.cursor.fetchone() is not None

    def record_sale(self, product_id: int, quantity: int) -> None:
        if quantity <= 0:
            raise ValueError("Quantity must be greater than 0.")

        if not self.storage.is_product_active(product_id):
            raise ValueError(f"Product {product_id} is inactive and cannot be sold.")

        query = "SELECT quantity FROM storage WHERE product_id = %s"
        self.db.cursor.execute(query, (product_id,))
        row = self.db.cursor.fetchone()
        available_quantity = row[0] if row else 0

        if available_quantity < quantity:
            raise ValueError(
                f"Insufficient stock in storage. Requested: {quantity}, Available: {available_quantity}."
            )

        query_insert = "INSERT INTO store_sales (product_id, quantity) VALUES (%s, %s)"
        try:
            self.db.cursor.execute(query_insert, (product_id, quantity))
            self.db.commit()
            print(f"Store sale recorded for ProductID {product_id}, Quantity: {quantity}.")
        except psycopg.Error as exc:
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

        query = "SELECT quantity FROM storage WHERE product_id = %s"
        self.db.cursor.execute(query, (product_id,))
        row = self.db.cursor.fetchone()
        available_quantity = row[0] if row else 0

        if available_quantity < quantity:
            raise ValueError(
                f"Insufficient stock in storage. Requested: {quantity}, Available: {available_quantity}."
            )

        query_insert = "INSERT INTO online_sales (product_id, quantity) VALUES (%s, %s)"
        try:
            self.db.cursor.execute(query_insert, (product_id, quantity))
            self.db.commit()
            print(f"Online sale recorded for ProductID {product_id}, Quantity: {quantity}.")
        except psycopg.Error as exc:
            print(f"Error recording online sale: {exc}")
            raise

    def check_product_exists(self, product_id: int) -> bool:
        query = "SELECT 1 FROM products WHERE product_id = %s"
        self.db.cursor.execute(query, (product_id,))
        return self.db.cursor.fetchone() is not None


class ReportManager:
    """Manages reporting operations."""

    def __init__(self, db: DatabaseConnection):
        self.db = db

    def get_sales_report(self) -> List[Tuple]:
        query = """
            SELECT
                p.product_id,
                p.product_name,
                p.price,
                COALESCE(s.quantity, 0) AS storage_quantity,
                COALESCE((SELECT SUM(ss.quantity) FROM store_sales ss WHERE ss.product_id = p.product_id), 0) AS store_sales_quantity,
                COALESCE((SELECT SUM(os.quantity) FROM online_sales os WHERE os.product_id = p.product_id), 0) AS online_sales_quantity,
                COALESCE((SELECT SUM(ss.quantity) FROM store_sales ss WHERE ss.product_id = p.product_id), 0) +
                COALESCE((SELECT SUM(os.quantity) FROM online_sales os WHERE os.product_id = p.product_id), 0) AS total_sales_quantity,
                p.availability
            FROM products p
            LEFT JOIN storage s ON p.product_id = s.product_id
            ORDER BY p.product_id
        """
        try:
            self.db.cursor.execute(query)
            return self.db.cursor.fetchall()
        except psycopg.Error as exc:
            print(f"Error generating sales report: {exc}")
            raise


class StoreApp:
    """Coordinates storage, sales, online shop, and reporting operations."""

    def __init__(self, database_url: str):
        self.db = DatabaseConnection(database_url)
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

    def update_product(self, product_id: int, name: str, price: float) -> None:
        self.storage.update_product(product_id, name, price)

    def delete_product(self, product_id: int) -> None:
        self.storage.hard_delete_product(product_id)

    def set_inventory_quantity(self, product_id: int, quantity: int) -> None:
        self.storage.set_inventory_quantity(product_id, quantity)

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
    from src.init_db import database_url

    app = StoreApp(database_url())
    try:
        app.start()
        app.display_inventory()
        app.display_sales_report()
    finally:
        app.stop()
