-- ساختار دیتابیس فروشگاه برای SQLite
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS Products (
    ProductID INTEGER PRIMARY KEY AUTOINCREMENT,
    ProductName TEXT NOT NULL,
    Price REAL NOT NULL,
    Availability INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS Storage (
    StorageID INTEGER PRIMARY KEY AUTOINCREMENT,
    ProductID INTEGER NOT NULL,
    Quantity INTEGER NOT NULL CHECK (Quantity >= 0),
    FOREIGN KEY (ProductID) REFERENCES Products(ProductID)
);

CREATE TABLE IF NOT EXISTS StoreSales (
    SaleID INTEGER PRIMARY KEY AUTOINCREMENT,
    ProductID INTEGER NOT NULL,
    SaleDate TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    Quantity INTEGER NOT NULL CHECK (Quantity > 0),
    FOREIGN KEY (ProductID) REFERENCES Products(ProductID)
);

CREATE TABLE IF NOT EXISTS OnlineSales (
    SaleID INTEGER PRIMARY KEY AUTOINCREMENT,
    ProductID INTEGER NOT NULL,
    SaleDate TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    Quantity INTEGER NOT NULL CHECK (Quantity > 0),
    FOREIGN KEY (ProductID) REFERENCES Products(ProductID)
);

DROP TRIGGER IF EXISTS trg_AfterStoreSale;
DROP TRIGGER IF EXISTS trg_AfterOnlineSale;

-- تریگر فروش حضوری: قبل از درج، چک موجودی + کاهش موجودی
CREATE TRIGGER IF NOT EXISTS trg_BeforeStoreSale
BEFORE INSERT ON StoreSales
FOR EACH ROW
BEGIN
  SELECT CASE 
    WHEN COALESCE((SELECT Quantity FROM Storage WHERE ProductID = NEW.ProductID), 0) < NEW.Quantity
    THEN RAISE(ABORT, 'موجودی کافی برای ProductID در Storage وجود ندارد')
  END;
  UPDATE Storage
    SET Quantity = Quantity - NEW.Quantity
    WHERE ProductID = NEW.ProductID;
  DELETE FROM Storage
    WHERE ProductID = NEW.ProductID AND Quantity = 0;
END;

CREATE TRIGGER IF NOT EXISTS trg_BeforeOnlineSale
BEFORE INSERT ON OnlineSales
FOR EACH ROW
BEGIN
  SELECT CASE 
    WHEN COALESCE((SELECT Quantity FROM Storage WHERE ProductID = NEW.ProductID), 0) < NEW.Quantity
    THEN RAISE(ABORT, 'موجودی کافی برای ProductID در Storage وجود ندارد')
  END;
  UPDATE Storage
    SET Quantity = Quantity - NEW.Quantity
    WHERE ProductID = NEW.ProductID;
  DELETE FROM Storage
    WHERE ProductID = NEW.ProductID AND Quantity = 0;
END;
INSERT INTO Products (ProductName, Price) VALUES
    ('Laptop Pro', 1200.00),
    ('Smartphone X', 600.00),
    ('Headphones', 150.00),
    ('Smartwatch', 250.00);

INSERT INTO Storage (ProductID, Quantity) VALUES
    (1, 20),
    (2, 30),
    (3, 50),
    (4, 15);
