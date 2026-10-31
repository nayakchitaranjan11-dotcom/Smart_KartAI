# SmartKart AI 🛒
### An Intelligent Grocery Delivery & Household Shopping Management System Using Python & Django

SmartKart AI is a full-stack, enterprise-grade web application and college major project designed to elevate quick-commerce and household grocery management. Built on a clean Python Django architecture with responsive vanilla CSS/JS, it introduces **five innovative AI and algorithmic features** addressing common modern grocery-shopping friction points: handwritten shopping lists, unmonitored monthly overspending, complex meal ingredient sourcing, supermarket food waste, and sudden out-of-stock disappointments.

---

## 🌟 5 Innovative Core Features

### 1. 📝 AI Grocery List Scanner
- **Visual Preprocessing & OCR Pipeline:** Cleans and sharpens handwritten or printed shopping list photos using Pillow (Grayscale $\rightarrow$ Contrast Enhancement $\rightarrow$ Unsharp Masking) and extracts text via `pytesseract`.
- **Intelligent Text & Quantity Parser:** Extracts item names, numerical quantities, and metrics (`kg`, `gms`, `litre`, `packets`, `dozen`) using multi-pattern tokenized regular expressions.
- **Fuzzy Catalogue Matcher:** Leverages Python's `difflib.SequenceMatcher` alongside token-intersection scoring to map imprecise list text to live catalogue products.
- **Graceful Fallback:** If Tesseract OCR is not installed or if an image is blurry, an interactive multi-line text editor allows instant manual parsing and verification.

### 2. 💰 Monthly Budget Smart Cart
- **Monthly Limit Tracker:** Sets a household monthly grocery allowance with an adjustable warning threshold (default 80%).
- **Live Cart Impact Projection:** Computes active order spending + current cart total to warn users before exceeding their monthly allowance.
- **Category Spending Analytics:** Interactive Chart.js breakdown visualizing where household grocery funds are allocated (Dairy, Staples, Snacks, Fresh Produce).
- **Money Saver Recommendations:** Analyzes cart items and highlights in-stock, cheaper alternatives within the same product category.

### 3. 🍲 Recipe-to-Cart Converter
- **Curated Multi-Cuisine Library:** North Indian, South Indian, Continental, and Healthy recipes with detailed cooking instructions and prep timings.
- **Dynamic Serving Scaler:** Dynamically recalibrates ingredient quantities for 2, 4, 6, or 8 people.
- **Pantry Exclusion Checklist:** Allows shoppers to uncheck ingredients they already have at home to avoid duplicate purchases.
- **One-Click Batch Cart Addition:** Adds all required in-stock ingredients directly to the shopping cart in a single atomic action.

### 4. ⏰ Expiry Rescue Deals
- **Food Waste Prevention:** Curated discount hub offering deep discounts (30%–70% off) on near-expiry perishable products (dairy, bakery, fresh items).
- **Dynamic Urgency Countdown:** Color-coded urgency badges:
  - 🔴 **Critical (Red):** Expires within 24 hours.
  - 🟠 **Urgent (Orange):** Expires within 3 days.
  - 🟡 **Warning (Yellow):** Expires within 7 days.
- **Automated Inventory Locking:** Products that cross their expiry date are automatically locked and hidden from active purchase.
- **Impact Counter:** Displays the total count of grocery items rescued from going to waste.

### 5. 🔄 Explainable Smart Product Substitution Engine
When an item is out of stock, the system evaluates candidate products against a multi-factor **100-point scoring algorithm**:
- **Category Match (35 pts):** Exact matching grocery category.
- **Nutritional & Tag Overlap (20 pts):** Attribute matching (*Organic, Whole Wheat, Low Fat, Toned*).
- **Pack Size Proximity (15 pts):** Weight/volume ratio closeness ($\pm 20\%$).
- **Brand Reputation (10 pts):** Brand matching or trusted manufacturer equivalence.
- **Price Compatibility (10 pts):** Proximity to the original item's price point.
- **Customer Rating (10 pts):** Star rating confidence ($4.0+\star$).

---

## 🚀 Version 2.0 Additions (Blinkit-style UX + Tkinter Desktop App)

> Full list of fixes and additions: see **[CHANGELOG.md](CHANGELOG.md)**. UI tools explained: see **[UI_UX_GUIDE.md](UI_UX_GUIDE.md)**.

- **⚡ Instant Cart Stepper:** product cards switch from **ADD** to a **[ − 1 + ]** stepper without reloading (AJAX JSON API).
- **🛒 Floating "View Cart" Bar:** live item count, total and a free-delivery progress hint on every shopping page.
- **🛵 Live Order Tracking Map:** animated SVG route (store → rider → home), ETA countdown, and status checks every 10 seconds.
- **🔔 Notification Center:** order updates, rider assignments, monthly budget alerts, and rescue-deal alerts for wishlisted items.
- **🔁 Order Again & Buy Again:** reorder a past order in one click, plus a "Buy Again" strip on the home page.
- **🧠 Frequently Bought Together:** association-rule (support/confidence) recommendations from real order history.
- **🎤 Voice Search:** say a product name (Web Speech API, Chrome/Edge).
- **🧮 Recipe Pack Calculator:** servings now change how many packs go into the cart (unit conversion g/kg/ml/L/tbsp/tsp).
- **🎨 Product Visual Tiles:** each product gets a matching emoji on a colour tile for its category (no photo files needed).
- **🛠️ Completed Admin:** recipe add/edit/delete, category edit, coupon on/off, rescue-deal on/off, rider duty toggle, Support Inbox, and every model registered in Django `/admin/`.
- **🖥️ Tkinter Store Manager Console (`desktop/`):** a desktop app built with **Tkinter** (Dashboard with Canvas charts, Inventory, Orders, Add Product, Alerts) that works on the same database as the website.
- **📴 Works Offline:** Bootstrap, the icons, Chart.js and the Inter font are bundled in `static/vendor/`.

---

## 👥 User Roles & Access Control

| Role | Default Username | Default Password | Key Capabilities |
| :--- | :--- | :--- | :--- |
| **Customer** | `customer` | `password123` | Browse catalogue, search autocomplete, AI list scanner, budget tracker, recipes, expiry rescue, cart & checkout, simulated UPI/Card/COD payments, ReportLab PDF invoices, order tracking. |
| **Administrator** | `admin` | `password123` | Comprehensive dashboard, inventory management with low-stock alerts, CRUD for products/categories/coupons/recipes/rescue deals, order status transitions, delivery partner assignment, customer analytics. |
| **Delivery Partner** | `delivery` | `password123` | Dedicated delivery portal, active delivery route map with simulated GPS navigation, one-click order status updates (`Picked Up` $\rightarrow$ `Out for Delivery` $\rightarrow$ `Delivered`), delivery history, performance metrics. |

---

## 🛠️ Technology Stack

- **Backend:** Python 3.10+, Django 5.x / 6.x (MTV Architecture, Django ORM, Class & Function Views)
- **Database:** SQLite (Relational Schema with foreign keys, cascading rules, indexing, and uniqueness constraints)
- **Frontend:** Semantic HTML5, Vanilla CSS3 (Custom Design System with Emerald Green & Fresh Lime palette), Vanilla JavaScript (ES6+), Bootstrap 5.3 (Grid & Utilities), Bootstrap Icons
- **Data Visualization:** Chart.js 4.x (Responsive spending donuts & monthly budget bars)
- **Document Generation:** ReportLab 4.x / 5.x (Printable PDF Tax Invoices with line items, tax breakdowns, and order metadata)
- **Image Processing & OCR:** Pillow 10+, Pytesseract 0.3.x (with manual text parsing fallback)
- **Desktop GUI:** Tkinter + ttk (Python standard library) for the Store Manager Console
- **Offline Front-end Assets:** Bootstrap 5.3.3, Bootstrap Icons 1.11.3, Chart.js 4.4.4 and Inter font served locally from `static/vendor/`

---

## 🚀 Quickstart Installation Guide

### 1. Clone or Extract the Project
```bash
cd SmartKartAI
```

### 2. Create and Activate a Python Virtual Environment
```bash
# Windows
python -m venv venv
venv\Scripts\activate

# macOS / Linux
python3 -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Optional: Install Tesseract OCR (for Image Scanning)
- **Windows:** Download and install from [UB-Mannheim Tesseract OCR](https://github.com/UB-Mannheim/tesseract/wiki). Ensure `tesseract.exe` is added to your system `PATH` or configured in `smartkart/settings.py` (`TESSERACT_CMD`).
- **macOS:** `brew install tesseract`
- **Linux (Ubuntu/Debian):** `sudo apt-get install tesseract-ocr`
> *Note: If Tesseract is not installed on your system, the application continues to work seamlessly through the built-in manual list editor and fuzzy regex matching engine.*

### 5. Apply Migrations & Seed Sample Data
```bash
# Run database migrations
python manage.py migrate

# Seed complete realistic database (Categories, 48 Indian Products, 8 Recipes, Coupons, Deals, Users)
python manage.py seed_data
```
> **Demoing weeks after seeding?** Fresh items (milk, paneer, tomatoes …) have real expiry dates, so they get locked as *expired* as time passes. Run `python manage.py seed_data --refresh-dates` to move every demo expiry date forward from today.

### 6. Run Automated Test Suite
```bash
python manage.py test
```

### 7. Launch the Development Server
```bash
python manage.py runserver
```
Visit **[http://127.0.0.1:8000/](http://127.0.0.1:8000/)** in your browser.

### 8. Optional: Launch the Tkinter Store Manager Console
```bash
python desktop/smartkart_desktop.py
```
Log in with `admin` / `password123`. The console uses the same `db.sqlite3` as the website, so changes show up in both. On Windows you can also double-click `desktop/run_desktop.bat`.

---

## 📂 Project Architecture

```
SmartKartAI/
├── apps/
│   ├── accounts/          # User authentication, Customer & Delivery profiles, Address book
│   ├── catalogue/         # Categories, Brands, Products, Low-stock alerts, Reviews
│   ├── cart/              # Cart sessions & user carts, Cart items, Coupons, Wishlist
│   ├── orders/            # Orders, Order items, Status history, ReportLab PDF invoices
│   ├── delivery/          # Delivery portal, Order assignment, Route simulation
│   ├── smart_features/    # OCR Scanner, Budget tracker, Recipes, Expiry rescue, Substitutions
│   ├── dashboard/         # Custom Admin management dashboard & analytics
│   └── core/              # Global context processors, Notifications, Contact, Seed command
├── smartkart/
│   ├── settings.py        # Django configuration, Static/Media roots, Context processors
│   ├── urls.py            # Global URL routing
│   └── wsgi.py            # WSGI application entry
├── static/
│   ├── css/main.css       # Custom design system (Emerald & Lime theme, components)
│   └── js/main.js         # Live search autocomplete, AJAX wishlist, recipe scaler
├── templates/
│   ├── base.html          # Responsive master layout, search dropdown, notifications
│   ├── accounts/          # Auth, Profile, Address management templates
│   ├── catalogue/         # Products grid, Category view, Product details, Search results
│   ├── cart/              # Cart detail, Wishlist templates
│   ├── orders/            # Checkout, Tracking timeline, History, Confirmation
│   ├── smart_features/    # Scanner, Budget dashboard, Recipes, Expiry rescue, Substitutions
│   ├── delivery/          # Delivery partner dashboard & fulfillment details
│   └── dashboard/         # Administrator control center & management views
├── desktop/
│   ├── smartkart_desktop.py   # Tkinter Store Manager Console (same DB via Django ORM)
│   └── run_desktop.bat        # Windows double-click launcher
├── static/vendor/             # Offline Bootstrap, Icons, Chart.js, Inter font
├── manage.py
├── requirements.txt
├── UI_UX_GUIDE.md             # UI tools explained + Tkinter comparison + viva Q&A
├── CHANGELOG.md               # Everything fixed / completed / added in v2.0
└── README.md
```

---

## 🧪 Automated Testing

SmartKart AI includes a comprehensive automated test suite covering model constraints, business logic, and algorithm correctness:
- **Catalogue:** Discount percentage calculations, stock check properties, expiry detection.
- **Cart & Coupons:** Quantity subtotals, free delivery threshold logic (₹499 cutoff), percentage & flat coupon discounts.
- **Orders:** Atomic stock deduction on order placement, automatic inventory restoration on cancellation.
- **Smart Features:** Fuzzy token-based OCR parsing, 6-factor explainable substitution scoring, monthly budget cart projections, recipe servings multiplication, and expiry urgency tiers.

- **Version 2.0 additions:** registration & safe login redirects, notifications, delivery workflow, admin CRUD & permissions, instant cart API, cancellation refunds, live tracking API, reorder, unit conversion, servings-aware recipes, recommendations, and regression tests for every bug fixed (**58 tests in total**).

Run all tests:
```bash
python manage.py test
```

---

## 🎓 Academic Project Disclaimer

- **Simulated Payment Gateway:** All payment methods (UPI, Credit/Debit Card, COD) simulate real-world e-commerce transaction lifecycles for academic demonstration without processing real money.
- **Simulated GPS Routing:** Delivery tracking coordinates and route progress are simulated to demonstrate live logistics workflows.
- **Original Work:** Developed as an original software engineering major project. All trademarks and brand names referenced in sample data belong to their respective owners.
