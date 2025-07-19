StoreDB Management System
Overview
The StoreDB Management System is a Python-based application designed to manage inventory and sales for a retail store. It interacts with a SQL Server database (StoreDB) to perform operations such as adding new products, updating inventory, recording store and online sales, and generating inventory reports. The system uses a command-line interface for ease of use and includes SQL triggers to automatically manage inventory levels after sales.
This project is ideal for small to medium-sized retail businesses looking to track products, manage stock, and monitor sales efficiently. It is built with modularity and extensibility in mind, making it easy to adapt for additional features or integration with other systems.
Features

Product Management: Add new products with names and prices to the database.
Inventory Management: Update product quantities in storage.
Sales Tracking: Record store and online sales with automatic inventory updates via SQL triggers.
Reporting: Generate a comprehensive inventory report showing product details, stock levels, and sales data.
Error Handling: Robust validation for product IDs, quantities, and stock availability.
Database Integration: Uses SQL Server with ODBC connectivity for reliable data storage.

Prerequisites
To run the StoreDB Management System, ensure you have the following installed:

Python 3.10+: The application is written in Python.
pyodbc: Python library for connecting to SQL Server. Install it using:pip install pyodbc


SQL Server: Microsoft SQL Server (Express or full version) with ODBC Driver 17 for SQL Server installed.
SQL Server Management Studio (SSMS) (optional): For manual database management and querying.

Database Setup
The application uses a SQL Server database named StoreDB. Follow these steps to set up the database:

Create the Database:Open SQL Server Management Studio (SSMS) or another SQL client and run the following script to create the database and tables:
...
_____________________________________________________________
Installation

Clone the Repository (if hosted on GitHub or similar):

cd storedb-management-system


Install Dependencies:Install the required Python package:
pip install pyodbc


Configure Database Connection:Update the database connection settings in the Python script (store_app.py or similar) to match your SQL Server configuration:
db = DatabaseConnection(server='.', database='StoreDB', driver='{ODBC Driver 17 for SQL Server}')


server: Use '.' for a local SQL Server instance or specify your server name/IP.
database: Must be StoreDB.
driver: Ensure {ODBC Driver 17 for SQL Server} is installed. Check available drivers with:import pyodbc
print(pyodbc.drivers())





Usage

Run the Application:Start the command-line interface by running:
python store_app.py


Interactive Menu:The application provides a menu with the following options:

1. Add New Product: Add a new product with a name and price.
2. Add Product to Inventory: Update the quantity of a product in storage.
3. Record Store Sale: Log a sale in the store, automatically updating inventory.
4. Record Online Sale: Log an online sale, automatically updating inventory.
5. Display Inventory: Show current inventory with product details and stock levels.
6. Clear Database: Remove all data from all tables (use with caution).
7. Exit: Close the application.

Example interaction:
Welcome to StoreDB Management System
1. Add New Product
2. Add Product to Inventory
3. Record Store Sale
4. Record Online Sale
5. Display Inventory
6. Clear Database
7. Exit
Enter your choice (1-7): 3
Enter ProductID: 16
Enter quantity to sell: 2
ثبت فروش در فروشگاه: 2 واحد از محصول با شناسه 16.


Error Handling:

The application validates inputs (e.g., positive quantities, valid ProductID).
SQL triggers prevent sales if there is insufficient stock in Storage.
User-friendly error messages are displayed for invalid inputs or database errors.

____________________________________________________
Contributing
Contributions are welcome! To contribute:

Fork the repository.
Create a feature branch (git checkout -b feature/your-feature).
Commit your changes (git commit -m "Add your feature").
Push to the branch (git push origin feature/your-feature).
Open a pull request.


