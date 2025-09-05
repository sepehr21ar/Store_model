import telebot
from store import StoreApp
from datetime import datetime

TOKEN = "YOUR_BOT_TOKEN_HERE"
bot = telebot.TeleBot(TOKEN)
app = StoreApp("store.db")
app.start()

def log_action_to_file(action: str):
    with open("action_flag.txt", "a", encoding="utf-8") as f:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        f.write(f"[{timestamp}] {action}\n")

@bot.message_handler(commands=['start'])
def start(message):
    bot.reply_to(
        message,
        "سلام 👋\nبه ربات مدیریت فروشگاه خوش آمدید.\nدستورات:\n"
        "/addproduct - افزودن محصول جدید\n"
        "/addinventory - افزودن موجودی کالا\n"
        "/sale_store - ثبت فروش حضوری\n"
        "/sale_online - ثبت فروش آنلاین\n"
        "/inventory - مشاهده موجودی\n"
        "/report - گزارش فروش\n"
        "/product_status - مدیریت وضعیت فعال/غیرفعال محصول"
    )

# افزودن محصول جدید
@bot.message_handler(commands=['addproduct'])
def add_product(message):
    msg = bot.reply_to(message, "نام محصول را وارد کنید:")
    bot.register_next_step_handler(msg, process_product_name)

def process_product_name(message):
    name = message.text
    msg = bot.reply_to(message, "قیمت محصول را وارد کنید:")
    bot.register_next_step_handler(msg, process_product_price, name)

def process_product_price(message, name):
    try:
        price = float(message.text)
        product_id = app.add_new_product(name, price)
        log_action_to_file(f"ProductAdded: ID={product_id} Name={name}")
        bot.reply_to(message, f"✅ محصول جدید ثبت شد با کد {product_id}")
    except Exception as e:
        bot.reply_to(message, f"❌ خطا: {e}")

# افزودن موجودی کالا
@bot.message_handler(commands=['addinventory'])
def add_inventory(message):
    msg = bot.reply_to(message, "کد محصول را وارد کنید:")
    bot.register_next_step_handler(msg, process_inventory_product)

def process_inventory_product(message):
    try:
        product_id = int(message.text)
        if not app.store.check_product_exists(product_id):
            bot.reply_to(message, f"❌ محصول با کد {product_id} وجود ندارد.")
            return
        msg = bot.reply_to(message, "تعداد موردنظر را وارد کنید:")
        bot.register_next_step_handler(msg, process_inventory_qty, product_id)
    except Exception as e:
        bot.reply_to(message, f"❌ خطا: {e}")

def process_inventory_qty(message, product_id):
    try:
        quantity = int(message.text)
        if quantity <= 0:
            bot.reply_to(message, "❌ تعداد باید بیشتر از صفر باشد.")
            return
        app.add_product_to_inventory(product_id, quantity)
        product = app.get_product_by_id(product_id)
        product_name = product.name if product else "Unknown"
        log_action_to_file(f"InventoryUpdated: ID={product_id}({product_name}) QTY={quantity}")
        bot.reply_to(message, f"✅ {quantity} عدد به موجودی محصول {product_name} اضافه شد.")
    except Exception as e:
        bot.reply_to(message, f"❌ خطا: {e}")

# ثبت فروش حضوری
@bot.message_handler(commands=['sale_store'])
def sale_store(message):
    msg = bot.reply_to(message, "کد محصول را وارد کنید:")
    bot.register_next_step_handler(msg, process_sale_store_product)

def process_sale_store_product(message):
    try:
        product_id = int(message.text)
        if not app.store.check_product_exists(product_id):
            bot.reply_to(message, f"❌ محصول با کد {product_id} وجود ندارد.")
            return
        if not app.storage.is_product_active(product_id):
            bot.reply_to(message, f"❌ محصول غیرفعال است و امکان فروش ندارد.")
            return
        msg = bot.reply_to(message, "تعداد فروش را وارد کنید:")
        bot.register_next_step_handler(msg, process_sale_store_qty, product_id)
    except Exception as e:
        bot.reply_to(message, f"❌ خطا: {e}")

def process_sale_store_qty(message, product_id):
    try:
        quantity = int(message.text)
        if quantity <= 0:
            bot.reply_to(message, "❌ تعداد باید بیشتر از صفر باشد.")
            return
        app.record_store_sale(product_id, quantity)
        product = app.get_product_by_id(product_id)
        product_name = product.name if product else "Unknown"
        log_action_to_file(f"StoreSale: ID={product_id}({product_name}) QTY={quantity}")
        bot.reply_to(message, f"✅ فروش حضوری ثبت شد برای محصول {product_name}")
    except Exception as e:
        bot.reply_to(message, f"❌ خطا: {e}")

# ثبت فروش آنلاین
@bot.message_handler(commands=['sale_online'])
def sale_online(message):
    msg = bot.reply_to(message, "کد محصول را وارد کنید:")
    bot.register_next_step_handler(msg, process_sale_online_product)

def process_sale_online_product(message):
    try:
        product_id = int(message.text)
        if not app.store.check_product_exists(product_id):
            bot.reply_to(message, f"❌ محصول با کد {product_id} وجود ندارد.")
            return
        if not app.storage.is_product_active(product_id):
            bot.reply_to(message, f"❌ محصول غیرفعال است و امکان فروش ندارد.")
            return
        msg = bot.reply_to(message, "تعداد فروش آنلاین را وارد کنید:")
        bot.register_next_step_handler(msg, process_sale_online_qty, product_id)
    except Exception as e:
        bot.reply_to(message, f"❌ خطا: {e}")

def process_sale_online_qty(message, product_id):
    try:
        quantity = int(message.text)
        if quantity <= 0:
            bot.reply_to(message, "❌ تعداد باید بیشتر از صفر باشد.")
            return
        app.record_online_sale(product_id, quantity)
        product = app.get_product_by_id(product_id)
        product_name = product.name if product else "Unknown"
        log_action_to_file(f"OnlineSale: ID={product_id}({product_name}) QTY={quantity}")
        bot.reply_to(message, f"✅ فروش آنلاین ثبت شد برای محصول {product_name}")
    except Exception as e:
        bot.reply_to(message, f"❌ خطا: {e}")

# مشاهده موجودی
@bot.message_handler(commands=['inventory'])
def inventory(message):
    try:
        inventory = app.storage.get_inventory()
        if not inventory:
            bot.reply_to(message, "📦 هیچ موجودی یافت نشد.")
            return
        text = "📦 موجودی:\n"
        for p in inventory:
            text += f"ID:{p.product_id} | {p.name} | قیمت:{p.price} | تعداد:{p.quantity}\n"
        bot.reply_to(message, text)
    except Exception as e:
        bot.reply_to(message, f"❌ خطا: {e}")

# گزارش فروش
@bot.message_handler(commands=['report'])
def report(message):
    try:
        report = app.report.get_sales_report()
        if not report:
            bot.reply_to(message, "📊 هیچ گزارشی یافت نشد.")
            return
        text = "📊 گزارش فروش:\n"
        for row in report:
            status = "فعال" if row[7] else "غیرفعال"
            text += (f"ID:{row[0]} | {row[1]} | قیمت:{row[2]} | موجودی:{row[3]} | "
                     f"فروش حضوری:{row[4]} | فروش آنلاین:{row[5]} | مجموع فروش:{row[6]} | وضعیت:{status}\n")
        bot.reply_to(message, text)
    except Exception as e:
        bot.reply_to(message, f"❌ خطا: {e}")

# فعال/غیرفعال کردن محصول
@bot.message_handler(commands=['product_status'])
def product_status(message):
    msg = bot.reply_to(message, "کد محصول را وارد کنید:")
    bot.register_next_step_handler(msg, process_product_status_id)

def process_product_status_id(message):
    try:
        product_id = int(message.text)
        msg = bot.reply_to(message, "فعال‌سازی یا غیرفعالسازی؟ (activate/deactivate):")
        bot.register_next_step_handler(msg, process_product_status_action, product_id)
    except Exception as e:
        bot.reply_to(message, f"❌ خطا: {e}")

def process_product_status_action(message, product_id):
    action = message.text.strip().lower()
    try:
        if action == "deactivate":
            app.storage.delete_product(product_id)
            log_action_to_file(f"ProductDeactivated: ID={product_id}")
            bot.reply_to(message, f"❌ محصول با کد {product_id} غیرفعال شد.")
        elif action == "activate":
            app.storage.activate_product(product_id)
            log_action_to_file(f"ProductActivated: ID={product_id}")
            bot.reply_to(message, f"✅ محصول با کد {product_id} فعال شد.")
        else:
            bot.reply_to(message, "⚠️ ورودی صحیح نیست (activate یا deactivate).")
    except Exception as e:
        bot.reply_to(message, f"❌ خطا: {e}")

print("🤖 Bot is running...")
bot.infinity_polling()
