import sqlite3
from pathlib import Path

def initialize_database(db_path='store.db', schema_file='store_schema.sql'):
    """راه‌اندازی اولیه دیتابیس و ایجاد ساختارها"""
    
    # بررسی وجود فایل دیتابیس
    db_exists = Path(db_path).exists()
    
    try:
        # اتصال به دیتابیس (اگر وجود نداشته باشد، ساخته می‌شود)
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # فعال کردن محدودیت‌های کلید خارجی
        cursor.execute("PRAGMA foreign_keys = ON")
        
        if not db_exists:
            print("🔹 ایجاد دیتابیس جدید...")
            # خواندن فایل اسکریپت SQL
            with open(schema_file, 'r', encoding='utf-8') as f:
                schema_script = f.read()
            
            # اجرای اسکریپت SQL
            cursor.executescript(schema_script)
            conn.commit()
            print("✅ دیتابیس با موفقیت ایجاد و مقداردهی اولیه شد.")
        else:
            print("🔹 دیتابیس از قبل وجود دارد. فقط اتصال برقرار شد.")
            
    except sqlite3.Error as e:
        print(f"❌ خطا در ایجاد دیتابیس: {e}")
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    print("📦 در حال راه‌اندازی سیستم مدیریت فروشگاه...")
    initialize_database()
    print("✨ عملیات با موفقیت انجام شد. دیتابیس آماده استفاده است.")