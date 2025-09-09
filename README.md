# 🛍️ Store Management System

## 📋 Overview

**Store Management System** is a comprehensive Python-based retail management application that provides multiple user interfaces for complete store operations. It connects to a **SQLite** database and offers functionalities such as:

- Adding new products  
- Managing stock levels  
- Recording in-store and online sales  
- Generating real-time inventory reports  
- Product activation/deactivation management
- Multi-interface support (CLI, Web UI, Telegram Bot)

It includes SQL **triggers** to automatically update inventory after sales, making it a reliable and efficient tool for small to medium-sized retail businesses.

## ✨ Features

- **Product Management**: Add new products with names and prices  
- **Inventory Management**: Update product quantities in storage  
- **Sales Tracking**: Record both in-store and online sales separately
- **Automatic Inventory Updates**: Triggered by SQL after each sale  
- **Multiple Interfaces**: CLI menu, Gradio web interface, and Persian Telegram bot
- **Reports**: View complete inventory and sales reports with detailed analytics
- **Product Status Control**: Activate/deactivate products for sales management
- **Error Handling**: Validates product IDs, quantities, and stock availability  
- **SQLite Integration**: Uses local database with automatic triggers
- **Action Logging**: Comprehensive logging system with timestamps

## 🛠️ Prerequisites

Ensure the following are installed on your system:

- **Python 3.8+**
- **gradio**: `pip install gradio`
- **pandas**: `pip install pandas` 
- **pyTelegramBotAPI**: `pip install pyTelegramBotAPI`

## 🧱 Database Setup

### 1. Initialize Database
Run the initialization script to create the SQLite database:

```bash
python init_db.py
```

This creates `store.db` with the following structure:

**Database Schema:**
- **Products**: Product information with availability status
- **Storage**: Current inventory levels  
- **StoreSales**: Physical store sales records
- **OnlineSales**: Online sales records
- **Triggers**: Automatic stock reduction on sales

### 2. Sample Data
The initialization includes sample products:
- Laptop Pro ($1200.00)
- Smartphone X ($600.00)  
- Headphones ($150.00)
- Smartwatch ($250.00)

## 📦 Installation

### 1. Clone the Repository
```bash
git clone https://github.com/sepehr21ar/Store_model
cd Store_model
```

### 2. Install Dependencies
```bash
pip install gradio pandas pyTelegramBotAPI
```

### 3. Initialize Database
```bash
python init_db.py
```

### 4. Run Your Preferred Interface

**CLI Interface:**
```bash
python store.py
```

**Web Interface (Gradio):**
```bash
python gradio_app.py
# Navigate to http://localhost:7860
```

**Telegram Bot:**
```bash
# Configure your bot token in telegram_bot.py first
python telegram_bot.py
```

## 🎯 Usage

### CLI Interface Menu
You will see an interactive menu with options:
1. Add New Product
2. Add Product to Inventory  
3. Delete Product
4. Record Store Sale
5. Record Online Sale
6. Show Current Inventory
7. Show Sales Report
8. Exit

### Web Interface Features
- Tabbed interface for different operations
- Real-time data tables for inventory and reports
- User-friendly forms with validation
- Status feedback for all operations

### Telegram Bot Commands
- Persian language interface
- Interactive button-based menu
- Real-time inventory updates
- Complete sales management

## 📁 Project Structure

```
Store_model/
├── store.py              # Core business logic and CLI interface
├── store_schema.sql      # Database schema and initial data
├── init_db.py           # Database initialization script
├── gradio_app.py        # Web UI using Gradio framework
├── telegram_bot.py      # Persian Telegram bot interface
├── store.db             # SQLite database (created after init)
├── action_flag.txt      # Operations log file
└── README.md            # Project documentation
```

## 🔧 Configuration

### Telegram Bot Setup
1. Create a bot via [@BotFather](https://t.me/botfather)
2. Replace `TOKEN` in `telegram_bot.py`:
```python
TOKEN = "YOUR_BOT_TOKEN_HERE"
```
3. Run: `python telegram_bot.py`

### Database Configuration
Default database path: `store.db`
Configurable in all interface files if needed.

## 🛡️ Error Handling

- Validates positive quantities and existing Product IDs
- Prevents sales if insufficient stock available
- Checks product availability status before sales
- User-friendly error messages on operation failures
- Comprehensive input validation across all interfaces
- Database connection error management
- Transaction rollback on trigger failures

## 📊 Key Operations

- **Add New Product**: Register products with name and price
- **Manage Inventory**: Add stock quantities to existing products
- **Record Sales**: Track store and online sales separately with automatic inventory updates
- **Generate Reports**: View inventory levels and comprehensive sales statistics
- **Product Management**: Activate/deactivate products for sales control
- **Data Export**: Action logging for audit trails

## 🔍 Technical Details

- **Backend**: Python with Object-Oriented Design
- **Database**: SQLite with automatic triggers for inventory management
- **Web Framework**: Gradio for interactive web interface
- **Bot Framework**: pyTelegramBotAPI with Persian language support
- **Architecture**: Separation of concerns with modular class design
- **Data Validation**: Multi-layer validation system
- **Logging**: Timestamp-based operation tracking

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature-name`
3. Test all interfaces thoroughly
4. Commit changes: `git commit -m 'Add feature-name'`
5. Push to branch: `git push origin feature-name`
6. Submit a Pull Request

## 🎯 Roadmap

- [ ] User authentication system
- [ ] REST API development
- [ ] Data export to Excel/PDF
- [ ] Advanced analytics and reporting
- [ ] Multi-language web interface
- [ ] Docker containerization
- [ ] Cloud database integration
- [ ] Mobile app development

## 🐛 Known Issues

- Telegram bot token is hardcoded (should use environment variables)
- Single-user system (no multi-user authentication)
- Local SQLite limitation (no concurrent access)
- No data backup/restore functionality

## 📝 License

This project is open-source under the MIT License. Use it freely for learning or commercial purposes. Contributions are encouraged!

## 📞 Support

For questions, bug reports, or feature requests:
- Create an issue on GitHub
- Check existing discussions
- Contact the development team

***

**Ready to efficiently manage your store operations with multiple interfaces!**