import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from store import StoreApp
from datetime import datetime

import os
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')

if not TOKEN:
    raise ValueError("TELEGRAM_BOT_TOKEN not found in environment variables")

bot = telebot.TeleBot(TOKEN)
app = StoreApp("store.db")
app.start()

def log_action_to_file(action: str):
    with open("action_flag.txt", "a", encoding="utf-8") as f:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        f.write(f"[{timestamp}] {action}\n")

# ------------------- ساخت منوی دکمه‌ای -------------------
def main_menu():
    markup = InlineKeyboardMarkup()
    markup.row_width = 2
    markup.add(
        InlineKeyboardButton("➕ افزودن محصول", callback_data="addproduct"),
        InlineKeyboardButton("📦 افزودن موجودی", callback_data="addinventory"),
        InlineKeyboardButton("🏪 فروش حضوری", callback_data="sale_store"),
        InlineKeyboardButton("🌐 فروش آنلاین", callback_data="sale_online"),
        InlineKeyboardButton("📋 موجودی کالا", callback_data="inventory"),
        InlineKeyboardButton("📊 گزارش فروش", callback_data="report"),
        InlineKeyboardButton("⚙️ فعال/غیرفعال محصول", callback_data="product_status"),
    )
    return markup

# ------------------- دستور استارت -------------------
@bot.message_handler(commands=['start'])
def start(message):
    bot.send_message(
        message.chat.id,
        "سلام 👋\nبه ربات مدیریت فروشگاه خوش آمدید.\nلطفاً یکی از گزینه‌های زیر را انتخاب کنید:",
        reply_markup=main_menu()
    )

# ------------------- مدیریت دکمه‌های منو -------------------
@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
    if call.data == "addproduct":
        msg = bot.send_message(call.message.chat.id, "نام محصول را وارد کنید:")
        bot.register_next_step_handler(msg, process_product_name)
    elif call.data == "addinventory":
        msg = bot.send_message(call.message.chat.id, "کد محصول را وارد کنید:")
        bot.register_next_step_handler(msg, process_inventory_product)
    elif call.data == "sale_store":
        msg = bot.send_message(call.message.chat.id, "کد محصول را وارد کنید:")
        bot.register_next_step_handler(msg, process_sale_store_product)
    elif call.data == "sale_online":
        msg = bot.send_message(call.message.chat.id, "کد محصول را وارد کنید:")
        bot.register_next_step_handler(msg, process_sale_online_product)
    elif call.data == "inventory":
        inventory(call.message)
    elif call.data == "report":
        report(call.message)
    elif call.data == "product_status":
        msg = bot.send_message(call.message.chat.id, "کد محصول را وارد کنید:")
        bot.register_next_step_handler(msg, process_product_status_id)

# ------------------- افزودن محصول -------------------
def process_product_name(message):
    name = message.text
    msg = bot.send_message(message.chat.id, "قیمت محصول را وارد کنید:")
    bot.register_next_step_handler(msg, process_product_price, name)

def process_product_price(message, name):
    try:
        price = float(message.text)
        product_id = app.add_new_product(name, price)
        log_action_to_file(f"ProductAdded: ID={product_id} Name={name}")
        bot.send_message(message.chat.id, f"✅ محصول جدید ثبت شد با کد {product_id}")
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ خطا: {e}")
    start(message)

# ------------------- افزودن موجودی -------------------
def process_inventory_product(message):
    try:
        product_id = int(message.text)
        if not app.store.check_product_exists(product_id):
            bot.send_message(message.chat.id, f"❌ محصول با کد {product_id} وجود ندارد.")
            return start(message)
        msg = bot.send_message(message.chat.id, "تعداد موردنظر را وارد کنید:")
        bot.register_next_step_handler(msg, process_inventory_qty, product_id)
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ خطا: {e}")
        start(message)

def process_inventory_qty(message, product_id):
    try:
        quantity = int(message.text)
        if quantity <= 0:
            bot.send_message(message.chat.id, "❌ تعداد باید بیشتر از صفر باشد.")
            return start(message)
        app.add_product_to_inventory(product_id, quantity)
        product = app.get_product_by_id(product_id)
        product_name = product.name if product else "Unknown"
        log_action_to_file(f"InventoryUpdated: ID={product_id}({product_name}) QTY={quantity}")
        bot.send_message(message.chat.id, f"✅ {quantity} عدد به موجودی محصول {product_name} اضافه شد.")
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ خطا: {e}")
    start(message)

# ------------------- فروش حضوری -------------------
def process_sale_store_product(message):
    try:
        product_id = int(message.text)
        if not app.store.check_product_exists(product_id):
            bot.send_message(message.chat.id, f"❌ محصول با کد {product_id} وجود ندارد.")
            return start(message)
        if not app.storage.is_product_active(product_id):
            bot.send_message(message.chat.id, f"❌ محصول غیرفعال است و امکان فروش ندارد.")
            return start(message)
        msg = bot.send_message(message.chat.id, "تعداد فروش را وارد کنید:")
        bot.register_next_step_handler(msg, process_sale_store_qty, product_id)
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ خطا: {e}")
        start(message)

def process_sale_store_qty(message, product_id):
    try:
        quantity = int(message.text)
        if quantity <= 0:
            bot.send_message(message.chat.id, "❌ تعداد باید بیشتر از صفر باشد.")
            return start(message)
        app.record_store_sale(product_id, quantity)
        product = app.get_product_by_id(product_id)
        product_name = product.name if product else "Unknown"
        log_action_to_file(f"StoreSale: ID={product_id}({product_name}) QTY={quantity}")
        bot.send_message(message.chat.id, f"✅ فروش حضوری ثبت شد برای محصول {product_name}")
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ خطا: {e}")
    start(message)

# ------------------- فروش آنلاین -------------------
def process_sale_online_product(message):
    try:
        product_id = int(message.text)
        if not app.store.check_product_exists(product_id):
            bot.send_message(message.chat.id, f"❌ محصول با کد {product_id} وجود ندارد.")
            return start(message)
        if not app.storage.is_product_active(product_id):
            bot.send_message(message.chat.id, f"❌ محصول غیرفعال است و امکان فروش ندارد.")
            return start(message)
        msg = bot.send_message(message.chat.id, "تعداد فروش آنلاین را وارد کنید:")
        bot.register_next_step_handler(msg, process_sale_online_qty, product_id)
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ خطا: {e}")
        start(message)

def process_sale_online_qty(message, product_id):
    try:
        quantity = int(message.text)
        if quantity <= 0:
            bot.send_message(message.chat.id, "❌ تعداد باید بیشتر از صفر باشد.")
            return start(message)
        app.record_online_sale(product_id, quantity)
        product = app.get_product_by_id(product_id)
        product_name = product.name if product else "Unknown"
        log_action_to_file(f"OnlineSale: ID={product_id}({product_name}) QTY={quantity}")
        bot.send_message(message.chat.id, f"✅ فروش آنلاین ثبت شد برای محصول {product_name}")
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ خطا: {e}")
    start(message)

# ------------------- مشاهده موجودی -------------------
@bot.message_handler(commands=['inventory'])
def inventory(message):
    try:
        inventory = app.storage.get_inventory()
        if not inventory:
            bot.send_message(message.chat.id, "📦 هیچ موجودی یافت نشد.")
            return start(message)
        text = "📦 موجودی:\n"
        for p in inventory:
            text += f"ID:{p.product_id} | {p.name} | قیمت:{p.price} | تعداد:{p.quantity}\n"
        bot.send_message(message.chat.id, text)
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ خطا: {e}")
    start(message)

# ------------------- گزارش فروش -------------------
@bot.message_handler(commands=['report'])
def report(message):
    try:
        report = app.report.get_sales_report()
        if not report:
            bot.send_message(message.chat.id, "📊 هیچ گزارشی یافت نشد.")
            return start(message)
        text = "📊 گزارش فروش:\n"
        for row in report:
            status = "فعال" if row[7] else "غیرفعال"
            text += (f"ID:{row[0]} | {row[1]} | قیمت:{row[2]} | موجودی:{row[3]} | "
                     f"فروش حضوری:{row[4]} | فروش آنلاین:{row[5]} | مجموع فروش:{row[6]} | وضعیت:{status}\n")
        bot.send_message(message.chat.id, text)
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ خطا: {e}")
    start(message)

# ------------------- فعال و غیرفعال کردن محصول -------------------
def process_product_status_id(message):
    try:
        product_id = int(message.text)
        msg = bot.send_message(message.chat.id, "فعال‌سازی یا غیرفعالسازی؟ (activate/deactivate):")
        bot.register_next_step_handler(msg, process_product_status_action, product_id)
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ خطا: {e}")
        start(message)

def process_product_status_action(message, product_id):
    action = message.text.strip().lower()
    try:
        if action == "deactivate":
            app.storage.delete_product(product_id)
            log_action_to_file(f"ProductDeactivated: ID={product_id}")
            bot.send_message(message.chat.id, f"❌ محصول با کد {product_id} غیرفعال شد.")
        elif action == "activate":
            app.storage.activate_product(product_id)
            log_action_to_file(f"ProductActivated: ID={product_id}")
            bot.send_message(message.chat.id, f"✅ محصول با کد {product_id} فعال شد.")
        else:
            bot.send_message(message.chat.id, "⚠️ ورودی صحیح نیست (activate یا deactivate).")
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ خطا: {e}")
    start(message)

# ------------------- اجرای ربات -------------------
print("🤖 Bot is running...")
bot.infinity_polling()
