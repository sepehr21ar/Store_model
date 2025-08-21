import telebot
import sqlite3
from datetime import datetime

TOKEN = "YOUR_BOT_TOKEN_HERE"
bot = telebot.TeleBot(TOKEN)

# ------------------ دیتابیس ------------------
def init_db():
    conn = sqlite3.connect("store.db")
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            price REAL,
            quantity INTEGER,
            status TEXT DEFAULT 'active'
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS sales (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id INTEGER,
            quantity INTEGER,
            type TEXT,
            date TEXT,
            FOREIGN KEY(product_id) REFERENCES products(id)
        )
    """)
    conn.commit()
    conn.close()

init_db()

# ------------------ دستورات ربات ------------------

@bot.message_handler(commands=['start'])
def start(message):
    bot.reply_to(message, "سلام 👋\nبه ربات فروشگاه خوش اومدی.\n\nدستورات:\n"
                          "/addproduct - افزودن محصول جدید\n"
                          "/inventory - مشاهده موجودی\n"
                          "/sale - ثبت فروش\n"
                          "/report - گزارش فروش")

# افزودن محصول
@bot.message_handler(commands=['addproduct'])
def add_product(message):
    msg = bot.reply_to(message, "نام محصول رو وارد کن:")
    bot.register_next_step_handler(msg, process_product_name)

def process_product_name(message):
    name = message.text
    msg = bot.reply_to(message, "قیمت محصول رو وارد کن:")
    bot.register_next_step_handler(msg, process_product_price, name)

def process_product_price(message, name):
    try:
        price = float(message.text)
    except ValueError:
        bot.reply_to(message, "⚠️ لطفا قیمت معتبر وارد کن.")
        return
    msg = bot.reply_to(message, "تعداد موجودی محصول رو وارد کن:")
    bot.register_next_step_handler(msg, process_product_quantity, name, price)

def process_product_quantity(message, name, price):
    try:
        quantity = int(message.text)
    except ValueError:
        bot.reply_to(message, "⚠️ لطفا عدد معتبر وارد کن.")
        return

    conn = sqlite3.connect("store.db")
    cur = conn.cursor()
    cur.execute("INSERT INTO products (name, price, quantity) VALUES (?, ?, ?)",
                (name, price, quantity))
    conn.commit()
    conn.close()

    bot.reply_to(message, f"✅ محصول {name} اضافه شد (قیمت: {price} | تعداد: {quantity})")

# موجودی
@bot.message_handler(commands=['inventory'])
def show_inventory(message):
    conn = sqlite3.connect("store.db")
    cur = conn.cursor()
    cur.execute("SELECT id, name, price, quantity, status FROM products")
    rows = cur.fetchall()
    conn.close()

    if not rows:
        bot.reply_to(message, "📦 موجودی خالی است.")
        return

    text = "📦 موجودی فعلی:\n\n"
    for r in rows:
        text += f"ID:{r[0]} | {r[1]} | قیمت:{r[2]} | تعداد:{r[3]} | وضعیت:{r[4]}\n"
    bot.reply_to(message, text)

# فروش
@bot.message_handler(commands=['sale'])
def sale_product(message):
    msg = bot.reply_to(message, "آیدی محصول رو وارد کن:")
    bot.register_next_step_handler(msg, process_sale_product)

def process_sale_product(message):
    try:
        product_id = int(message.text)
    except ValueError:
        bot.reply_to(message, "⚠️ آیدی معتبر وارد کن.")
        return

    msg = bot.reply_to(message, "تعداد فروش رو وارد کن:")
    bot.register_next_step_handler(msg, process_sale_quantity, product_id)

def process_sale_quantity(message, product_id):
    try:
        quantity = int(message.text)
    except ValueError:
        bot.reply_to(message, "⚠️ لطفا عدد معتبر وارد کن.")
        return

    conn = sqlite3.connect("store.db")
    cur = conn.cursor()
    cur.execute("SELECT quantity FROM products WHERE id=?", (product_id,))
    row = cur.fetchone()

    if not row:
        bot.reply_to(message, "❌ محصول پیدا نشد.")
        conn.close()
        return

    current_qty = row[0]
    if current_qty < quantity:
        bot.reply_to(message, "❌ موجودی کافی نیست.")
        conn.close()
        return

    # کاهش موجودی و ثبت فروش
    cur.execute("UPDATE products SET quantity=? WHERE id=?", (current_qty - quantity, product_id))
    cur.execute("INSERT INTO sales (product_id, quantity, type, date) VALUES (?, ?, ?, ?)",
                (product_id, quantity, "offline", datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    conn.commit()
    conn.close()

    bot.reply_to(message, f"✅ فروش ثبت شد (محصول ID:{product_id} | تعداد:{quantity})")

# گزارش فروش
@bot.message_handler(commands=['report'])
def show_report(message):
    conn = sqlite3.connect("store.db")
    cur = conn.cursor()
    cur.execute("""SELECT p.name, s.quantity, s.type, s.date 
                   FROM sales s JOIN products p ON s.product_id = p.id""")
    rows = cur.fetchall()
    conn.close()

    if not rows:
        bot.reply_to(message, "📊 هنوز فروشی ثبت نشده.")
        return

    text = "📊 گزارش فروش:\n\n"
    for r in rows:
        text += f"{r[0]} | تعداد:{r[1]} | نوع:{r[2]} | تاریخ:{r[3]}\n"
    bot.reply_to(message, text)

# ------------------ اجرای ربات ------------------
print("🤖 Bot is running...")
bot.infinity_polling()
