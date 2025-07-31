import sqlite3
from typing import List, Tuple, Optional
from datetime import datetime
from dataclasses import dataclass

@dataclass
class Product:
    """Represents a product in the store."""
    product_id: int
    name: str
    price: float
    quantity: int

class DatabaseConnection:
    """Manages connection to SQLite database."""
    def __init__(self, db_path: str = "store.db"):
        self.db_path = db_path
        self.conn = None
        self.cursor = None

    def connect(self) -> None:
        """Establishes connection to the database."""
        try:
            self.conn = sqlite3.connect(self.db_path,check_same_thread=False)
            self.cursor = self.conn.cursor()
            print("Successfully connected to SQLite database.")
            # Enable foreign key constraints
            self.cursor.execute("PRAGMA foreign_keys = ON")
        except sqlite3.Error as e:
            print(f"Connection error: {e}")
            raise

    def close(self) -> None:
        """Closes cursor and connection."""
        if self.cursor:
            self.cursor.close()
        if self.conn:
            self.conn.close()
            print("Database connection closed.")

    def commit(self) -> None:
        """Commits the current transaction."""
        if self.conn:
            self.conn.commit()

class StorageManager:
    """Manages storage operations."""
    def __init__(self, db: DatabaseConnection):
        self.db = db

    def add_product(self, product_id: int, quantity: int) -> None:
        """Adds or updates product quantity in Storage."""
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
        """Retrieves current inventory from Storage."""
        query = '''
            SELECT p.ProductID, p.ProductName, p.Price, COALESCE(s.Quantity, 0) AS Quantity
            FROM Products p
            LEFT JOIN Storage s ON p.ProductID = s.ProductID
        '''
        try:
            self.db.cursor.execute(query)
            rows = self.db.cursor.fetchall()
            return [Product(row[0], row[1], row[2], row[3]) for row in rows]
        except sqlite3.Error as e:
            print(f"Error retrieving inventory: {e}")
            raise

    def add_new_product(self, name: str, price: float) -> int:
        """Add a new product to the Products table and return its ID."""
        query = '''
            INSERT INTO Products (ProductName, Price, Availability)
            VALUES (?, ?, 1)
        '''
        try:
            self.db.cursor.execute(query, (name, price))
            self.db.commit()
            product_id = self.db.cursor.lastrowid
            print(f"Added new product: {name} with ID {product_id}.")
            return int(product_id)
        except sqlite3.Error as e:
            print(f"Error adding new product: {e}")
            raise

    def is_product_active(self, product_id: int) -> bool:
        query = "SELECT Availability FROM Products WHERE ProductID = ?"
        self.db.cursor.execute(query, (product_id,))
        row = self.db.cursor.fetchone()
        return row and row[0] == 1

    def delete_product(self, product_id: int) -> None:
        query = "UPDATE Products SET Availability = 0 WHERE ProductID = ?"
        try:
            self.db.cursor.execute(query, (product_id,))
            self.db.commit()
            print(f"❌ ProductID {product_id} marked as inactive.")
        except sqlite3.Error as e:
            print(f"Error deactivating product: {e}")
            raise

    def activate_product(self, product_id: int) -> None:
        """Marks a product as active (Available)."""
        query = "UPDATE Products SET Availability = 1 WHERE ProductID = ?"
        try:
            self.db.cursor.execute(query, (product_id,))
            self.db.commit()
            print(f"✅ ProductID {product_id} marked as active.")
        except sqlite3.Error as e:
            print(f"Error activating product: {e}")
            raise

class StoreManager:
    def __init__(self, db: DatabaseConnection):
        self.db = db
        self.storage = StorageManager(db)

    def check_product_exists(self, product_id: int) -> bool:
        "Checks whether the ProductID exists in the Products table."
        query = "SELECT 1 FROM Products WHERE ProductID = ?"
        self.db.cursor.execute(query, (product_id,))
        return self.db.cursor.fetchone() is not None

    def record_sale(self, product_id: int, quantity: int):
        if not self.storage.is_product_active(product_id):
            print(f"❌ Product {product_id} is inactive and cannot be sold.")
            return
        if not self.storage.is_product_active(product_id):
            raise ValueError(f"The product with ID {product_id} is inactive and cannot be sold.")
        if quantity <= 0:
            print("❌ Quantity must be greater than 0.")
            return

        query = '''
            INSERT INTO StoreSales (ProductID, Quantity, SaleDate)
            VALUES (?, ?, ?)
        '''
        try:
            self.db.cursor.execute(query, (product_id, quantity, datetime.now().isoformat()))
            self.db.commit()
            print(f"✅ Store sale recorded for ProductID {product_id}, Quantity: {quantity}")
        except sqlite3.Error as e:
            print(f"❌ Error recording store sale: {e}")
            raise

class OnlineShopManager:
    """Manages online shop sales."""
    def __init__(self, db: DatabaseConnection):
        self.db = db
        self.storage = StorageManager(db)

    def record_sale(self, product_id: int, quantity: int) -> None:
        if not self.check_product_exists(product_id):
            raise ValueError(f"The product with ID {product_id} does not exist in the products table.")
        if not self.storage.is_product_active(product_id):
            raise ValueError(f"The product with ID {product_id} is inactive and cannot be sold.")
        if quantity <= 0:
            raise ValueError("Quantity must be greater than 0.")

        query = '''
            INSERT INTO OnlineSales (ProductID, Quantity, SaleDate)
            VALUES (?, ?, ?)
        '''
        try:
            self.db.cursor.execute(query, (product_id, quantity, datetime.now().isoformat()))
            self.db.commit()
            print(f"✅ Online sale recorded for ProductID {product_id}, Quantity: {quantity}")
        except sqlite3.Error as e:
            print(f"❌ Error recording online sale: {e}")
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
        """Generates a report combining Products, Storage, StoreSales, and OnlineSales."""
        query = '''
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
            FROM 
                Products p
            LEFT JOIN 
                Storage s ON p.ProductID = s.ProductID
            ORDER BY 
                p.ProductID;
        '''
        try:
            self.db.cursor.execute(query)
            return self.db.cursor.fetchall()
        except sqlite3.Error as e:
            print(f"Error generating sales report: {e}")
            raise

class StoreApp:
    """Main application to coordinate storage, store, online shop, and reporting operations."""
    def __init__(self, db_path: str = "store.db"):
        self.db = DatabaseConnection(db_path)
        self.storage = StorageManager(self.db)
        self.store = StoreManager(self.db)
        self.online_shop = OnlineShopManager(self.db)
        self.report = ReportManager(self.db)

    def start(self) -> None:
        """Starts the application and connects to the database."""
        self.db.connect()

    def stop(self) -> None:
        """Stops the application and closes the database connection."""
        self.db.close()
    
    def get_product_by_id(self, product_id: int) -> Optional[Product]:
        inventory = self.storage.get_inventory()
        for product in inventory:
            if product.product_id == product_id:
                return product
        return None

    def add_product_to_inventory(self, product_id: int, quantity: int) -> None:
        """Adds a product to inventory."""
        self.storage.add_product(product_id, quantity)

    def add_new_product(self, name: str, price: float) -> int:
        """Adds a new product to Products table."""
        return self.storage.add_new_product(name, price)

    def record_store_sale(self, product_id: int, quantity: int) -> None:
        """Records a sale in the store."""
        self.store.record_sale(product_id, quantity)

    def record_online_sale(self, product_id: int, quantity: int) -> None:
        """Records a sale in the online shop."""
        self.online_shop.record_sale(product_id, quantity)

    def display_inventory(self) -> None:
        """Displays current inventory."""
        inventory = self.storage.get_inventory()
        print("\nCurrent Inventory:")
        for product in inventory:
            print(f"ProductID: {product.product_id}, Name: {product.name}, "
                  f"Price: {product.price}, Quantity: {product.quantity}")

    def display_sales_report(self) -> None:
        """Displays sales report."""
        report = self.report.get_sales_report()
        print("\nSales Report:")
        for row in report:
            status = "✅ Active" if row[7] else "🚫 Inactive"
            print(f"ProductID: {row[0]}, Name: {row[1]}, "
                  f"Price: {row[2]}, Storage: {row[3]}, "
                  f"Store Sales: {row[4]}, Online Sales: {row[5]}, "
                  f"Total Sales: {row[6]}, Status: {status}")

    def run_interactive(self):
        while True:
            print("\n🛍️ Store Management Menu")
            print("1. Add new product")
            print("2. Add product to storage")
            print("3. Delete product")
            print("4. Record store sale")
            print("5. Record online sale")
            print("6. Show current inventory")
            print("7. Show sales report")
            print("8. Exit")

            choice = input("Enter your choice (1-8): ")

            try:
                if choice == '1':
                    name = input("Enter product name: ")
                    price = float(input("Enter product price: "))
                    product_id = self.add_new_product(name, price)
                    print(f"✅ Product added with ProductID: {product_id}")

                elif choice == '2':
                    product_id = int(input("Enter ProductID: "))
                    if not self.store.check_product_exists(product_id):
                        print(f"❌ Error: ProductID {product_id} does not exist.")
                        continue
                    quantity = int(input("Enter quantity to add: "))
                    if quantity <= 0:
                        print("❌ Quantity must be greater than 0.")
                        continue
                    self.add_product_to_inventory(product_id, quantity)

                elif choice == '3':
                    product_id = int(input("Enter ProductID to delete: "))
                    confirm = input(f"⚠️ Are you sure you want to deactivate ProductID {product_id}? (yes/no): ").strip().lower()
                    if confirm == 'yes':
                        self.storage.delete_product(product_id)
                    else:
                        print("❌ Deactivation cancelled.")

                elif choice == '4':
                    product_id = int(input("Enter ProductID: "))
                    quantity = int(input("Enter quantity sold (store): "))
                    self.record_store_sale(product_id, quantity)

                elif choice == '5':
                    product_id = int(input("Enter ProductID: "))
                    quantity = int(input("Enter quantity sold (online): "))
                    self.record_online_sale(product_id, quantity)

                elif choice == '6':
                    self.display_inventory()

                elif choice == '7':
                    self.display_sales_report()

                elif choice == '8':
                    print("👋 Exiting the program...")
                    break

                else:
                    print("❌ Invalid choice. Please enter a number between 1 and 8.")

            except ValueError as e:
                print(f"⚠️ Invalid input: {e}")
            except Exception as e:
                print(f"❌ Error: {e}")

if __name__ == "__main__":
    app = StoreApp("store.db")

    try:
        app.start()
        app.run_interactive()
    finally:
        app.stop()