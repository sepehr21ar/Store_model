import gradio as gr
import pandas as pd
from store import StoreApp
import os
from datetime import datetime
from llm_sql import chat_with_llm


def log_action_to_file(action: str):
    """Log performed actions to a flag file."""
    with open("action_flag.txt", "a", encoding="utf-8") as f:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        f.write(f"[{timestamp}] {action}\n")


app = StoreApp("store.db")

def start_app():
    try:
        app.start()
        return "✅ Successfully connected to the SQLite database."
    except Exception as e:
        return f"❌ Database connection error: {e}"


def add_new_product(name: str, price: str):
    try:
        price = float(price)
        product_id = app.add_new_product(name, price)
        log_action_to_file(f"ProductAdded: ID={product_id} Name={name}")
        return f"✅ Product added with ID {product_id}.", "", ""
    except ValueError as e:
        return f"❌ Invalid input: {e}", name, price
    except Exception as e:
        return f"❌ Error adding product: {e}", name, price


def add_to_inventory(product_id: str, quantity: str):
    try:
        product_id = int(product_id)
        quantity_ = int(quantity)
        if quantity_ <= 0:
            return "❌ Quantity must be greater than zero.", product_id, quantity

        if not app.store.check_product_exists(product_id):
            return f"❌ Product ID {product_id} does not exist.", product_id, quantity

        product = app.get_product_by_id(product_id)
        product_name = product.name if product else "Unknown"

        app.add_product_to_inventory(product_id, quantity_)
        log_action_to_file(f"InventoryUpdated: ID={product_id}({product_name}) QTY={quantity_}")
        return f"✅ {quantity_} units added to inventory for Product ID {product_id}.", "", ""
    except ValueError as e:
        return f"❌ Invalid input: {e}", product_id, quantity
    except Exception as e:
        return f"❌ Error adding to inventory: {e}", product_id, quantity


def record_store_sale(product_id: str, quantity: str):
    try:
        product_id = int(product_id)
        quantity = int(quantity)

        if not app.store.check_product_exists(product_id):
            return f"❌ Product ID {product_id} does not exist.", product_id, quantity

        if not app.storage.is_product_active(product_id):
            return f"❌ Product ID {product_id} is inactive and cannot be sold.", product_id, quantity

        if quantity <= 0:
            return "❌ Quantity must be greater than zero.", product_id, quantity

        app.record_store_sale(product_id, quantity)

        product = app.get_product_by_id(product_id)
        product_name = product.name if product else "Unknown"
        log_action_to_file(f"StoreSale: ID={product_id}({product_name}) QTY={quantity}")

        return f"✅ Store sale recorded for Product ID {product_id}, Quantity: {quantity}.", "", ""

    except ValueError as e:
        return f"❌ Invalid input: {e}", product_id, quantity
    except Exception as e:
        return f"❌ Error recording store sale: {e}", product_id, quantity
    
    


def record_online_sale(product_id: str, quantity: str):
    try:
        product_id = int(product_id)
        quantity = int(quantity)

        if not app.store.check_product_exists(product_id):
            return f"❌ Product ID {product_id} does not exist.", product_id, quantity

        if not app.storage.is_product_active(product_id):
            return f"❌ Product ID {product_id} is inactive and cannot be sold.", product_id, quantity

        if quantity <= 0:
            return "❌ Quantity must be greater than zero.", product_id, quantity

        app.record_online_sale(product_id, quantity)

        product = app.get_product_by_id(product_id)
        product_name = product.name if product else "Unknown"
        log_action_to_file(f"OnlineSale: ID={product_id}({product_name}) QTY={quantity}")

        return f"✅ Online sale recorded for Product ID {product_id}, Quantity: {quantity}.", "", ""

    except ValueError as e:
        return str(e), product_id, quantity
    except Exception as e:
        return f"❌ Error recording online sale: {e}", product_id, quantity



def show_inventory():
    try:
        inventory = app.storage.get_inventory()
        if not inventory:
            return pd.DataFrame(), "⚠️ No inventory data found."
        data = [{
            "Product ID": product.product_id,
            "Name": product.name,
            "Price": f"{product.price:.2f}",
            "Quantity": product.quantity
        } for product in inventory]
        return pd.DataFrame(data), "✅ Inventory loaded."
    except Exception as e:
        return pd.DataFrame(), f"❌ Error loading inventory: {e}"


def show_sales_report():
    try:
        report = app.report.get_sales_report()
        if not report:
            return pd.DataFrame(), "⚠️ No sales data found."
        data = [{
            "Product ID": row[0],   # ProductID
            "Name": row[1],         # ProductName
            "Price": f"{row[2]:.2f}",   # Price
            "Inventory": row[3],    # StorageQuantity
            "Store Sales": row[4],  # StoreSalesQuantity
            "Online Sales": row[5], # OnlineSalesQuantity
            "Total Sales": row[6],  # TotalSalesQuantity
            "Status": "Active" if row[7] else "Inactive"   # Availability
        } for row in report]
        return pd.DataFrame(data), "✅ Sales report loaded."
    except Exception as e:
        return pd.DataFrame(), f"❌ Error loading sales report: {e}"


def manage_product_status(product_id: str, action: str):
    try:
        product_id = int(product_id)
        if action == "Deactivate":
            app.storage.delete_product(product_id)
            log_action_to_file(f"ProductDeactivated: ID={product_id}")
            return f"❌ Product ID {product_id} deactivated.", ""
        elif action == "Activate":
            app.storage.activate_product(product_id)
            log_action_to_file(f"ProductActivated: ID={product_id}")
            return f"✅ Product ID {product_id} activated.", ""
        else:
            return "⚠️ Invalid action selected.", product_id
    except ValueError as e:
        return f"❌ Invalid input: {e}", product_id
    except Exception as e:
        return f"❌ Error: {e}", product_id


# Gradio Interface
with gr.Blocks(css="h1 {text-align: center;}") as demo:
    gr.Markdown("# 🛍️ Store Management System")
    gr.Markdown("Use the tabs below to manage products, inventory, sales, and reports. Results will display in each tab.")

    with gr.Tab("Connect to Database"):
        start_btn = gr.Button("Connect")
        start_output = gr.Textbox(label="Connection Status", interactive=False)
        start_btn.click(fn=start_app, outputs=start_output)

    with gr.Tab("Add New Product"):
        name_input = gr.Textbox(label="Product Name")
        price_input = gr.Textbox(label="Product Price")
        add_product_btn = gr.Button("Add Product")
        add_product_output = gr.Textbox(label="Result", interactive=False)
        add_product_btn.click(
            fn=add_new_product,
            inputs=[name_input, price_input],
            outputs=[add_product_output, name_input, price_input]
        )

    with gr.Tab("Add to Inventory"):
        product_id_input = gr.Textbox(label="Product ID")
        quantity_input = gr.Textbox(label="Quantity")
        add_inventory_btn = gr.Button("Add to Inventory")
        add_inventory_output = gr.Textbox(label="Result", interactive=False)
        add_inventory_btn.click(
            fn=add_to_inventory,
            inputs=[product_id_input, quantity_input],
            outputs=[add_inventory_output, product_id_input, quantity_input]
        )

    with gr.Tab("Record Store Sale"):
        store_sale_product_id = gr.Textbox(label="Product ID")
        store_sale_quantity = gr.Textbox(label="Quantity")
        store_sale_btn = gr.Button("Record Sale")
        store_sale_output = gr.Textbox(label="Result", interactive=False)
        store_sale_btn.click(
            fn=record_store_sale,
            inputs=[store_sale_product_id, store_sale_quantity],
            outputs=[store_sale_output, store_sale_product_id, store_sale_quantity]
        )

    with gr.Tab("Record Online Sale"):
        online_sale_product_id = gr.Textbox(label="Product ID")
        online_sale_quantity = gr.Textbox(label="Quantity")
        online_sale_btn = gr.Button("Record Sale")
        online_sale_output = gr.Textbox(label="Result", interactive=False)
        online_sale_btn.click(
            fn=record_online_sale,
            inputs=[online_sale_product_id, online_sale_quantity],
            outputs=[online_sale_output, online_sale_product_id, online_sale_quantity]
        )

    with gr.Tab("View Inventory"):
        inventory_btn = gr.Button("Load Inventory")
        inventory_df = gr.Dataframe(label="Current Inventory")
        inventory_output = gr.Textbox(label="Status", interactive=False)
        inventory_btn.click(fn=show_inventory, outputs=[inventory_df, inventory_output])

    with gr.Tab("Sales Report"):
        report_btn = gr.Button("Load Report")
        report_df = gr.Dataframe(label="Sales Report")
        report_output = gr.Textbox(label="Status", interactive=False)
        report_btn.click(fn=show_sales_report, outputs=[report_df, report_output])

    with gr.Tab("Manage Product Status"):
        manage_product_id = gr.Textbox(label="Product ID")
        action_choice = gr.Radio(choices=["Activate", "Deactivate"], label="Select Action")
        manage_btn = gr.Button("Submit")
        manage_output = gr.Textbox(label="Result", interactive=False)
        manage_btn.click(
            fn=manage_product_status,
            inputs=[manage_product_id, action_choice],
            outputs=[manage_output, manage_product_id]
        )
 
    with gr.Tab("💬 Chat with Database (LLM)"):
        chatbot = gr.Chatbot(label="Database Assistant", type="messages")
        msg = gr.Textbox(label="Type your question")
        clear = gr.Button("Clear Chat")
        chat_output = gr.Textbox(label="Status", interactive=False)

        def user_message(user_msg, history):
            if not user_msg:
                # خروجی: [chatbot, chatbot, msg, chat_output]
                return [], [], "", "⚠️ لطفاً یک سوال وارد کنید."
            
            history = history or []
            history.append({"role": "user", "content": user_msg})
            
            # خروجی: [chatbot, chatbot, msg, chat_output]
            return history, history, "", ""   # سوم msg خالی میشه، چهارم chat_output خالی


        msg.submit(
        user_message,
        [msg, chatbot],
        [chatbot, chatbot, msg, chat_output]  # ۴ تا خروجی
    ).then(
        chat_with_llm,
        chatbot,
        [chatbot, chat_output],
        queue=True
    )

        clear.click(lambda: ([], "", ""), None, [chatbot, msg, chat_output])





if __name__ == "__main__":
    try:
        import os

        os.environ["NO_PROXY"] = "127.0.0.1,localhost"
        os.environ["no_proxy"] = "127.0.0.1,localhost"

        demo.launch(
    server_name="0.0.0.0",
    server_port=7860,
    share=False,
    show_api=False,
    inbrowser=True  
)





    finally:
        app.stop()
