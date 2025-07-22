# 🛍️ StoreDB Management System

## 📋 Overview

**StoreDB Management System** is a Python-based CLI application designed to manage inventory and sales for a retail store. It connects to a **Microsoft SQL Server** database and offers functionalities such as:

- Adding new products  
- Managing stock levels  
- Recording in-store and online sales  
- Generating real-time inventory reports  

It includes SQL **triggers** to automatically update inventory after sales, making it a reliable and efficient tool for small to medium-sized retail businesses.



## ✨ Features

- **Product Management**: Add new products with names and prices  
- **Inventory Management**: Update product quantities in storage  
- **Sales Tracking**: Record both in-store and online sales  
- **Automatic Inventory Updates**: Triggered by SQL after each sale  
- **Reports**: View a complete inventory report with product and sales data  
- **Error Handling**: Validates product IDs, quantities, and stock availability  
- **SQL Server Integration**: Uses `pyodbc` for seamless database connectivity


## 🛠️ Prerequisites

Ensure the following are installed on your system:

- **Python 3.10+**
- **pyodbc**  
  Install via pip:
  ```bash
  pip install pyodbc

Microsoft SQL Server (Express or full version)

ODBC Driver 17 for SQL Server

SQL Server Management Studio (SSMS) (optional)


🧱 Database Setup
1. Create the Database and Tables
Use SQL Server Management Studio or any SQL client and execute the following SQL script:

<details> <summary>📂 Click to expand SQL setup</summary>

--->

IF EXISTS (SELECT name FROM sys.databases WHERE name = N'StoreDB')
BEGIN
    ALTER DATABASE StoreDB SET SINGLE_USER WITH ROLLBACK IMMEDIATE;
    DROP DATABASE StoreDB;
END
GO

CREATE DATABASE StoreDB;
GO
USE StoreDB;
GO

-- Products Table
CREATE TABLE Products (
    ProductID INT PRIMARY KEY IDENTITY(1,1),
    ProductName NVARCHAR(70) NOT NULL,
    Price DECIMAL(10,2) NOT NULL
);
GO

-- Store Sales Table
CREATE TABLE StoreSales (
    SaleID INT PRIMARY KEY IDENTITY(1,1),
    ProductID INT NOT NULL,
    SaleDate DATETIME NOT NULL DEFAULT GETDATE(),
    Quantity INT NOT NULL CHECK (Quantity > 0),
    FOREIGN KEY (ProductID) REFERENCES Products(ProductID)
);
GO

-- Storage Table
CREATE TABLE Storage (
    StorageID INT PRIMARY KEY IDENTITY(1,1),
    ProductID INT NOT NULL,
    Quantity INT NOT NULL CHECK (Quantity >= 0),
    FOREIGN KEY (ProductID) REFERENCES Products(ProductID)
);
GO

-- Online Sales Table
CREATE TABLE OnlineSales (
    SaleID INT PRIMARY KEY IDENTITY(1,1),
    ProductID INT NOT NULL,
    SaleDate DATETIME NOT NULL DEFAULT GETDATE(),
    Quantity INT NOT NULL CHECK (Quantity > 0),
    FOREIGN KEY (ProductID) REFERENCES Products(ProductID)
);
GO

</details>
2. Add SQL Triggers
<details> <summary>⚙️ Inventory update triggers</summary>

-- Trigger after store sale
CREATE TRIGGER trg_AfterStoreSale
ON StoreSales
AFTER INSERT
AS
BEGIN
    SET NOCOUNT ON;
    DECLARE @ProductID INT, @Quantity INT;
    DECLARE sale_cursor CURSOR FOR 
        SELECT ProductID, Quantity FROM inserted;

    OPEN sale_cursor;
    FETCH NEXT FROM sale_cursor INTO @ProductID, @Quantity;

    WHILE @@FETCH_STATUS = 0
    BEGIN
        IF EXISTS (SELECT 1 FROM Storage WHERE ProductID = @ProductID AND Quantity >= @Quantity)
        BEGIN
            UPDATE Storage
            SET Quantity = Quantity - @Quantity
            WHERE ProductID = @ProductID;

            DELETE FROM Storage WHERE ProductID = @ProductID AND Quantity = 0;
        END
        ELSE
        BEGIN
            RAISERROR ('Not enough stock for ProductID %d in Storage.', 16, 1, @ProductID);
            ROLLBACK TRANSACTION;
            RETURN;
        END
        FETCH NEXT FROM sale_cursor INTO @ProductID, @Quantity;
    END

    CLOSE sale_cursor;
    DEALLOCATE sale_cursor;
END;
GO

-- Trigger after online sale
CREATE TRIGGER trg_AfterOnlineSale
ON OnlineSales
AFTER INSERT
AS
BEGIN
    SET NOCOUNT ON;
    DECLARE @ProductID INT, @Quantity INT;
    DECLARE sale_cursor CURSOR FOR 
        SELECT ProductID, Quantity FROM inserted;

    OPEN sale_cursor;
    FETCH NEXT FROM sale_cursor INTO @ProductID, @Quantity;

    WHILE @@FETCH_STATUS = 0
    BEGIN
        IF EXISTS (SELECT 1 FROM Storage WHERE ProductID = @ProductID AND Quantity >= @Quantity)
        BEGIN
            UPDATE Storage
            SET Quantity = Quantity - @Quantity
            WHERE ProductID = @ProductID;

            DELETE FROM Storage WHERE ProductID = @ProductID AND Quantity = 0;
        END
        ELSE
        BEGIN
            RAISERROR ('Not enough stock for ProductID %d in Storage.', 16, 1, @ProductID);
            ROLLBACK TRANSACTION;
            RETURN;
        END
        FETCH NEXT FROM sale_cursor INTO @ProductID, @Quantity;
    END

    CLOSE sale_cursor;
    DEALLOCATE sale_cursor;
END;
GO


</details>
3. Insert Sample Data

INSERT INTO Products (ProductName, Price) VALUES
    ('Laptop Pro', 1200.00),
    ('Smartphone X', 600.00),
    ('Headphones', 150.00),
    ('Smartwatch', 250.00);
GO

INSERT INTO Storage (ProductID, Quantity) VALUES
    (1, 20),
    (2, 30),
    (3, 50),
    (4, 15);
GO

📦 Installation
1. Clone the Repository
gh repo clone sepehr21ar/Store_model

2. Install Dependencies
pip install pyodbc

3. Configure Database Connection
Update the connection config in store_app.py:

db = DatabaseConnection(
    server='.', 
    database='StoreDB', 
    driver='{ODBC Driver 17 for SQL Server}'
)

You will see an interactive menu:
1. Add New Product
2. Add Product to Inventory
3. Record Store Sale
4. Record Online Sale
5. Display Inventory
6. Clear Database
7. Exit


🛡 Error Handling
Validates positive quantities and existing Product IDs

Prevents sales if insufficient stock

User-friendly error messages on failure

I will check posible errors...
🤝 Contributing
Fork the repository

This project is open-source. Use it freely for learning or commercial use. Contributions are encouraged!
wait for other projects
