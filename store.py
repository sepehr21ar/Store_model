import pyodbc
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
    """Manages connection to SQL Server database."""
    def __init__(self, server: str, database: str, driver: str):
        self.server = server
        self.database = database
        self.driver = driver
        self.conn = None
        self.cursor = None

    def connect(self) -> None:
        """Establishes connection to the database."""
        try:
            self.conn = pyodbc.connect(
                f'DRIVER={self.driver};SERVER={self.server};DATABASE={self.database};Trusted_Connection=yes'
            )
            self.cursor = self.conn.cursor()
            print("Successfully connected to the database.")
        except pyodbc.Error as e:
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
        query = '''
            IF EXISTS (SELECT 1 FROM Storage WHERE ProductID = ?)
                UPDATE Storage SET Quantity = Quantity + ? WHERE ProductID = ?
            ELSE
                INSERT INTO Storage (ProductID, Quantity) VALUES (?, ?)
        '''
        try:
            self.db.cursor.execute(query, (product_id, quantity, product_id, product_id, quantity))
            self.db.commit()
            print(f"Added {quantity} units of ProductID {product_id} to Storage.")
        except pyodbc.Error as e:
            print(f"Error adding product to storage: {e}")
            raise

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
            return [Product(row.ProductID, row.ProductName, row.Price, row.Quantity) for row in rows]
        except pyodbc.Error as e:
            print(f"Error retrieving inventory: {e}")
            raise

    def add_new_product(self, name: str, price: float) -> int:
        "Add a new product to the Products table and return its ID."
        query = '''
            INSERT INTO Products (ProductName, Price)
            OUTPUT INSERTED.ProductID
            VALUES (?, ?)
        '''
        try:
            self.db.cursor.execute(query, (name, price))
            product_id = self.db.cursor.fetchone()[0]
            self.db.commit()
            print(f"Added new product: {name} with ID {product_id}.")
            return int(product_id)
        except pyodbc.Error as e:
            print(f"Error adding new product: {e}")
            raise

from datetime import datetime

class StoreManager:
    def __init__(self, db: DatabaseConnection):
        self.db = db

    def check_product_exists(self, product_id: int) -> bool:
        "Checks whether the ProductID exists in the Products table."
        query = "SELECT 1 FROM Products WHERE ProductID = ?"
        self.db.cursor.execute(query, (product_id,))
        return self.db.cursor.fetchone() is not None

    def record_sale(self, product_id: int, quantity: int) -> None:
        """Record a sale in the table StoreSales."""
        if not self.check_product_exists(product_id):
            raise ValueError(f"The product with ID {product_id} does not exist in the products table.")
        if quantity <= 0:
            raise ValueError("quentity must be greater than 0.")
        query = '''
            INSERT INTO StoreSales (ProductID, Quantity, SaleDate)
            VALUES (?, ?, ?)
        '''
        try:
            self.db.cursor.execute(query, (product_id, quantity, datetime.now()))
            self.db.commit()
            print(f"Record in Store {quantity} nubmer of product with ID : {product_id}.")
        except pyodbc.Error as e:
            if 'Insufficient stock' in str(e):
                print(f"Error: Insufficient stock for product with ID {product_id} does not exist")
            else:
                print(f"Error in recording sales in the store: {e}")
            raise
        
class OnlineShopManager:
    """Manages online shop sales."""
    def __init__(self, db: DatabaseConnection):
        self.db = db

    def record_sale(self, product_id: int, quantity: int) -> None:
        if not self.check_product_exists(product_id):
            raise ValueError(f"The product with ID {product_id} does not exist in the products table.")
        if quantity <= 0:
            raise ValueError("quentity must be greater than 0.")
        query = '''
            INSERT INTO OnlineSales (ProductID, Quantity, SaleDate)
            VALUES (?, ?, ?)
        '''
        try:
            self.db.cursor.execute(query, (product_id, quantity, datetime.now()))
            self.db.commit()
            print(f"Record in Store {quantity} nubmer of product with ID : {product_id}.")
        except pyodbc.Error as e:
            if 'Insufficient stock' in str(e):
                print(f"There is not enough stock for product with ID {product_id}. Please check stock.")
            else:
                print(f"An error occurred: Please contact your system administrator (details: {e}).")
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
    COALESCE(SUM(ss.Quantity), 0) AS StoreSalesQuantity,
    COALESCE(SUM(os.Quantity), 0) AS OnlineSalesQuantity,
    COALESCE(SUM(COALESCE(ss.Quantity, 0)) + SUM(COALESCE(os.Quantity, 0)), 0) AS TotalSalesQuantity
FROM 
    Products p
LEFT JOIN 
    Storage s ON p.ProductID = s.ProductID
LEFT JOIN 
    StoreSales ss ON p.ProductID = ss.ProductID
LEFT JOIN 
    OnlineSales os ON p.ProductID = os.ProductID
GROUP BY 
    p.ProductID, p.ProductName, p.Price, COALESCE(s.Quantity, 0)
ORDER BY 
    p.ProductID;
        '''
        try:
            self.db.cursor.execute(query)
            return self.db.cursor.fetchall()
        except pyodbc.Error as e:
            print(f"Error generating sales report: {e}")
            raise

class StoreApp:
    """Main application to coordinate storage, store, online shop, and reporting operations."""
    def __init__(self, server: str, database: str, driver: str):
        self.db = DatabaseConnection(server, database, driver)
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
            print(f"ProductID: {row.ProductID}, Name: {row.ProductName}, "
                  f"Price: {row.Price}, Storage: {row.StorageQuantity}, "
                  f"Store Sales: {row.StoreSalesQuantity}, Online Sales: {row.OnlineSalesQuantity}, "
                  f"Total Sales: {row.TotalSalesQuantity}")

    def run_interactive(self) -> None:
        """Runs an interactive command-line interface."""
        while True:
            print("\nStore Management System")
            print("1. Add new product")
            print("2. Add product to inventory")
            print("3. Record store sale")
            print("4. Record online sale")
            print("5. Display inventory")
            print("6. Display sales report")
            print("7. Exit")
            choice = input("Enter your choice (1-7): ")

            try:
                if choice == '1':
                    name = input("Enter product name: ")
                    price = float(input("Enter product price: "))
                    product_id = self.add_new_product(name, price)
                    print(f"Product added with ProductID: {product_id}")

                elif choice == '2':
                    product_id = int(input("Enter ProductID: "))
                    # بررسی وجود ProductID
                    if not self.store.check_product_exists(product_id):
                        print(f"خطا: محصول با شناسه {product_id} در جدول محصولات وجود ندارد.")
                        continue  # بازگشت به منوی اصلی بدون انجام اقدام دیگر
                    quantity = int(input("Enter quantity to add: "))
                    if quantity <= 0:
                        print("خطا: تعداد باید مثبت باشد.")
                        continue
                    self.add_product_to_inventory(product_id, quantity)

                elif choice == '3':
                    product_id = int(input("Enter ProductID: "))
                    quantity = int(input("Enter quantity sold: "))
                    self.record_store_sale(product_id, quantity)

                elif choice == '4':
                    product_id = int(input("Enter ProductID: "))
                    quantity = int(input("Enter quantity sold: "))
                    self.record_online_sale(product_id, quantity)

                elif choice == '5':
                    self.display_inventory()

                elif choice == '6':
                    self.display_sales_report()

                elif choice == '7':
                    print("Exiting...")
                    break

                else:
                    print("Invalid choice. Please enter a number between 1 and 7.")

            except ValueError as e:
                print(f"Invalid input: {e}")
            except Exception as e:
                print(f"Error: {e}")

if __name__ == "__main__":
    # Initialize the application
    app = StoreApp(
        server='.',  # Replace with your SQL Server name (e.g., localhost)
        database='StoreDB',
        driver='{ODBC Driver 17 for SQL Server}'  # Use installed ODBC driver
    )

    try:
        app.start()
        app.run_interactive()
    finally:
        app.stop()