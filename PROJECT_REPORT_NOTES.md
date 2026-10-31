# SmartKart AI — College Major Project Documentation & Report Notes

## Project Title
**SmartKart AI: An Intelligent Grocery Delivery and Household Shopping Management System Using Python and Django**

---

## 1. Abstract
The rapid evolution of quick-commerce and online grocery delivery has transformed modern consumer shopping habits. However, conventional grocery platforms primarily function as passive digital storefronts—failing to address pervasive consumer friction points such as unbudgeted monthly spending, manual conversion of handwritten household shopping lists, complex ingredient estimation for home recipes, supermarket food wastage due to near-expiry items, and abrupt out-of-stock experiences.

**SmartKart AI** is a full-stack, enterprise-grade web application built using Python and the Django framework that bridges these gaps through algorithmic intelligence and user-centric workflows. It introduces five flagship innovations: (1) an **AI Grocery List Scanner** using image pre-processing, OCR, tokenized regex parsing, and fuzzy catalogue matching; (2) a **Monthly Budget Smart Cart** with real-time cart spending projection, threshold warnings, and category-level spending analytics; (3) a **Recipe-to-Cart Converter** featuring dynamic serving scaling, stock checks, and pantry exclusion checklists; (4) an **Expiry Rescue Deals** module that dynamically discounts and categorizes near-expiry perishables to prevent food waste; and (5) an **Explainable Smart Product Substitution Engine** that computes 6-factor similarity scores to recommend relevant in-stock alternatives. The system supports three distinct user roles (Customer, Administrator, and Delivery Partner) with dedicated responsive portals, ReportLab PDF tax invoices, and simulated end-to-end order tracking.

---

## 2. Problem Statement & Motivation

### Key Problems Identified:
1. **Manual Friction with Handwritten Lists:** Shoppers and homemakers frequently maintain physical notes or message snippets for household groceries. Manually searching and adding dozens of items individually on e-commerce apps is tedious and error-prone.
2. **Impulse Buying & Unmonitored Overspending:** Standard e-commerce platforms incentivize impulse purchases without alerting shoppers when they are about to exceed their monthly household grocery allowance.
3. **Recipe Cooking Inefficiencies:** Preparing meals from recipes requires manually calculating ingredient quantities for different family sizes, searching for each ingredient separately, and accidentally repurchasing items already present in the kitchen pantry.
4. **Food Wastage in Quick-Commerce:** Retail warehouses discard tons of edible groceries daily due to imminent shelf-life expiry because platforms lack dedicated urgency-tiered rescue mechanisms.
5. **Out-of-Stock Frustration:** When a preferred grocery brand or pack size is unavailable, shoppers either abandon their carts or face inappropriate automated replacements.

---

## 3. Existing System vs. Proposed SmartKart AI System

| Dimension | Existing Quick-Commerce Apps | SmartKart AI (Proposed System) |
| :--- | :--- | :--- |
| **Grocery List Input** | Manual search bar item by item | Automated image OCR upload + regex quantity parser + fuzzy catalogue match + manual list editor fallback |
| **Budget Management** | None; encourages unrestricted cart expansion | Monthly budget tracking, live cart impact projection, 80% threshold alerts, and Money Saver cheaper swaps |
| **Recipe Sourcing** | Standalone blogs with no direct inventory integration | Integrated recipe library, dynamic serving multiplier (2/4/6/8), pantry exclusion, and 1-click batch cart addition |
| **Perishable Management** | Hidden markdown or discard at warehouse level | Public Expiry Rescue Deals hub with dynamic urgency countdown (Red/Orange/Yellow), rescue counter, and auto-locking |
| **Out-of-Stock Handling** | Generic "Notify Me" or opaque substitutions | 6-factor explainable scoring engine (Category, Tags, Size, Brand, Price, Rating) with transparent match reasoning |
| **Invoicing & Documents** | Simple digital summary | Downloadable ReportLab PDF tax invoices with itemized tables, GST breakdowns, and order metadata |
| **Role Separation** | Separate third-party apps required | Unified multi-role web platform (Customer, Admin Portal, Delivery Partner Portal) |

---

## 4. System Requirements

### 4.1 Software Requirements
- **Operating System:** Windows 10/11, macOS, or Linux (Ubuntu 20.04+)
- **Programming Language:** Python 3.10 to 3.12+
- **Web Framework:** Django 5.x / 6.x
- **Database:** SQLite (Development/Evaluation) / PostgreSQL (Production ready)
- **Image Processing / OCR:** Pillow 10.x, Pytesseract 0.3.x, Tesseract-OCR Binary (optional)
- **Document Generation:** ReportLab 4.x / 5.x
- **Frontend Stack:** Semantic HTML5, Vanilla CSS3, Vanilla JavaScript (ES6+), Bootstrap 5.3, Bootstrap Icons, Chart.js 4.x

### 4.2 Hardware Requirements
- **Processor:** Dual-Core 2.0 GHz or higher (Intel Core i3/i5/i7 or AMD Ryzen)
- **RAM:** Minimum 4 GB (8 GB recommended for concurrent OCR processing)
- **Storage:** 500 MB free hard disk space for codebase, database, and uploaded media assets

---

## 5. Architectural Design

```
+-----------------------------------------------------------------------------------+
|                                 Client Layer                                      |
|   Responsive Web Browser (Customer Portal / Admin Dashboard / Delivery Portal)   |
|   Bootstrap 5.3 Grid + Vanilla CSS Design System + Vanilla JS + Chart.js          |
+------------------------------------------+----------------------------------------+
                                           | HTTP Requests / Form Data / Media
                                           v
+-----------------------------------------------------------------------------------+
|                           Django Presentation & Routing Layer                     |
|   Global URLs Routing -> App Views (Accounts, Catalogue, Cart, Orders, etc.)     |
|   Custom Role Decorators (@customer_required, @admin_required, @delivery_required)|
|   Global Context Processors (Cart Count, Wishlist, Categories, Budget Status)     |
+------------------------------------------+----------------------------------------+
                                           |
                                           v
+-----------------------------------------------------------------------------------+
|                               Business Logic Layer                                |
|  - OCR Grocery Scanner Pipeline (Pillow Image Preprocessing + Regex + Difflib)   |
|  - Monthly Budget Smart Engine (Projections, Chart.js Data, Cheaper Swaps)       |
|  - Recipe Scaler & Inventory Mapper (Dynamic Portions + Pantry Exclusions)        |
|  - Expiry Rescue Service (Urgency Tiers + Food Waste Locking)                    |
|  - 6-Factor Explainable Smart Substitution Engine                                |
|  - ReportLab PDF Tax Invoice Generator                                           |
+------------------------------------------+----------------------------------------+
                                           | ORM Queries
                                           v
+-----------------------------------------------------------------------------------+
|                             Persistence Layer (Django ORM)                        |
|   User, CustomerProfile, DeliveryProfile, Address, Category, Brand, Product,      |
|   Cart, CartItem, Coupon, Wishlist, Order, OrderItem, StatusHistory,              |
|   MonthlyBudget, Recipe, RecipeIngredient, ExpiryRescueDeal, GroceryScan          |
|   SQLite / PostgreSQL Database Engine                                             |
+-----------------------------------------------------------------------------------+
```

---

## 6. Algorithmic Formulations

### 6.1 Explainable Product Substitution Scoring Formula
Let $P_t$ be the target out-of-stock product and $P_c$ be a candidate in-stock product within the same or related category. The total match score $S(P_t, P_c) \in [0, 100]$ is computed as:

$$S(P_t, P_c) = W_{\text{cat}} \cdot M_{\text{cat}} + W_{\text{tag}} \cdot M_{\text{tag}} + W_{\text{size}} \cdot M_{\text{size}} + W_{\text{brand}} \cdot M_{\text{brand}} + W_{\text{price}} \cdot M_{\text{price}} + W_{\text{rating}} \cdot M_{\text{rating}}$$

Where the weights and metrics are defined as:
1. **Category Match ($W_{\text{cat}} = 35$):** $M_{\text{cat}} = 1.0$ if $\text{Category}(P_c) == \text{Category}(P_t)$, else $0.4$ for related sub-categories.
2. **Nutritional / Tag Overlap ($W_{\text{tag}} = 20$):**
   $$M_{\text{tag}} = \frac{|\text{Tags}(P_t) \cap \text{Tags}(P_c)|}{\max(|\text{Tags}(P_t)|, 1)}$$
3. **Pack Size Proximity ($W_{\text{size}} = 15$):**
   $$R_{\text{size}} = \frac{\text{UnitValue}(P_c)}{\text{UnitValue}(P_t)}, \quad M_{\text{size}} = \begin{cases} 1.0 & \text{if } 0.8 \le R_{\text{size}} \le 1.25 \\ 0.55 & \text{if } 0.5 \le R_{\text{size}} \le 2.0 \\ 0.0 & \text{otherwise} \end{cases}$$
4. **Brand Reputation ($W_{\text{brand}} = 10$):** $M_{\text{brand}} = 1.0$ if $\text{Brand}(P_c) == \text{Brand}(P_t)$, else $0.4$ for other reputable brands.
5. **Price Proximity ($W_{\text{price}} = 10$):**
   $$M_{\text{price}} = \frac{\min(\text{Price}(P_t), \text{Price}(P_c))}{\max(\text{Price}(P_t), \text{Price}(P_c))}$$
6. **Customer Rating ($W_{\text{rating}} = 10$):**
   $$M_{\text{rating}} = \frac{\text{Rating}(P_c)}{5.0}$$

---

### 6.2 Fuzzy Token-Based OCR Matching Formula
For each parsed grocery text query $Q$ with tokens $T_Q = \text{tokenize}(Q)$ and catalogue product name $P$ with tokens $T_P = \text{tokenize}(P)$:

$$\text{Confidence}(Q, P) = \left( 0.45 \cdot \text{SeqRatio}(Q, P) + 0.40 \cdot \frac{|T_Q \cap T_P|}{|T_Q|} + \text{Bonus}_{\text{sub}} + \text{Bonus}_{\text{cat}} \right) \times 100$$

Where:
- $\text{SeqRatio}(Q, P) = 2 \cdot \frac{|M|}{|Q| + |P|}$ (Ratcliff-Obershelp sequence similarity via `difflib`)
- $\text{Bonus}_{\text{sub}} = 0.20$ if $Q$ is a substring of $P$
- $\text{Bonus}_{\text{cat}} = 0.15$ if any token in $T_Q$ matches the product's category title

---

## 7. Functional Modules Overview

1. **`accounts` App:**
   - Multi-role registration & login with role redirection.
   - Profile management with customizable monthly budget allowances.
   - Customer address book with default selection, full address validation, and postal codes.
2. **`catalogue` App:**
   - Multi-category hierarchy (8 main categories with distinct SVG icons).
   - Product browsing with sorting (Price, Newest, Rating, Discount), search autocomplete with debouncing.
   - Product detail view with real-time stock availability, nutritional badges, expiry dates, and verified customer reviews.
3. **`cart` App:**
   - Session-backed guest carts merging into database carts upon user login.
   - Percentage and flat coupon engine with minimum purchase validation and usage caps.
   - Subtotal, delivery fee calculation (free above ₹499), and customer wishlist management.
4. **`orders` App:**
   - 2-step checkout with delivery slot selection (Instant 15-min Express vs Scheduled Slots).
   - Academic payment simulations (UPI QR, Card, Cash on Delivery).
   - ReportLab PDF tax invoice generator with complete tax invoices downloadable per order.
   - Live order tracking timeline with step-by-step state visualization.
5. **`smart_features` App:**
   - AI Grocery List Scanner with OCR and manual multi-line editor fallback.
   - Monthly Budget Tracker with live cart projection and Chart.js spending analytics.
   - Recipe-to-Cart module with dynamic serving multipliers (2/4/6/8) and pantry exclusion checklist.
   - Expiry Rescue Deals with dynamic urgency countdowns and rescued food counter.
   - Explainable Smart Product Substitution engine.
6. **`delivery` App:**
   - Dedicated delivery partner dashboard displaying pending and active assigned orders.
   - Simulated interactive delivery route map with destination coordinates.
   - One-click order state transitions (`Assigned` $\rightarrow$ `Picked Up` $\rightarrow$ `Out for Delivery` $\rightarrow$ `Delivered`).
7. **`dashboard` App:**
   - Administrative management portal with KPI overview cards (Total Revenue, Active Orders, Rescued Items).
   - Inventory manager with low-stock warnings and one-click reorder triggers.
   - Full CRUD operations for Products, Categories, Recipes, Coupons, and Rescue Deals.
8. **`core` App:**
   - Global context processors feeding cart count, categories, wishlist, and budget status across all templates.
   - Custom template filters and automated database seeder (`seed_data` management command).

---

## 8. Limitations & Future Scope

### Limitations:
- **Optical Character Recognition (OCR):** Recognition accuracy on heavily degraded, cursive, or low-contrast handwritten images relies on good lighting conditions.
- **Payment & GPS Integration:** Real-world payment gateways (Razorpay, Stripe) and live driver GPS telematics are simulated for academic safety and cost-free demonstration.

### Future Scope:
- **Multilingual OCR & Voice Ordering:** Incorporate Indian regional language recognition (Hindi, Tamil, Bengali) and speech-to-text ordering for voice-driven list creation.
- **IoT Smart Pantry Integration:** Connect with smart kitchen jars and weight sensors to auto-generate shopping lists when essential items run low.
- **Micro-Warehouse Multi-Store Routing:** Extend single-store inventory to multi-dark-store nearest-depot routing using Dijkstra's algorithm.


---

## 9. Version 2.0 Enhancements (Completion Phase)

### 9.1 Defects found during testing and fixed
| Defect | Root cause | Resolution |
| :--- | :--- | :--- |
| All-products page crashed | Template used the custom filter `make_list_split` without `{% load core_tags %}` | Added the template library load |
| Discount sorting crashed | ORM `order_by()` on a Python `@property` | Annotated a SQL expression $(MRP - SP)/MRP$ cast to float |
| Budget settings never saved | Missing `timezone` import, hidden by a broad `except` | Import added; regression test written |
| Wrong tracking step highlighted | Timeline list (6 steps) indexed with the status list (8 statuses) | Explicit status → step mapping |
| Admin cancellation kept stock deducted | Stock restoration existed only in the customer view | Moved into the model method `Order.cancel()` (single source of truth) |
| Recipe servings ignored when adding to cart | Quantity hard-coded to 1 | Unit-conversion engine computes packs needed |

### 9.2 New algorithms

**(a) Pack quantity estimation (Recipe-to-Cart)**
$$\text{packs} = \max\left(1,\ \left\lceil \frac{q_{\text{ingredient}} \times \frac{\text{servings}}{\text{base servings}} \times f_{\text{unit}}}{\text{pack size} \times f_{\text{pack unit}}} \right\rceil\right)$$
where $f$ converts kg→1000 g, L→1000 ml, tbsp→15, tsp→5. If the units can't be compared (e.g. *pieces* vs *grams*), it falls back to 1 pack.

**(b) Frequently Bought Together (association rules / market-basket analysis)**
$$\text{confidence}(A \Rightarrow B) = \frac{\text{support}(A \cup B)}{\text{support}(A)} = \frac{\#\text{orders containing A and B}}{\#\text{orders containing A}}$$
Candidates are ranked by confidence. Cold start (no order history yet) falls back to products that share a recipe, then to the top-rated products in the same category.

**(c) Simulated express ETA**
Each order stage has a base number of minutes left (Placed 18 → Out for Delivery 5). Minutes already spent in the current stage are subtracted, but never past 3 minutes and never below 1. The tracking page asks the JSON API every 10 s.

### 9.3 New modules
- `apps/core/notifications.py`: event-driven notification engine (order, budget, rescue, system)
- `apps/smart_features/units.py`: unit conversion and pack calculation
- `apps/smart_features/recommendation_engine.py`: Frequently Bought Together + Buy Again
- `apps/cart` JSON APIs `api/state/` and `api/set/`: instant cart stepper
- `apps/orders` endpoints `status.json` and `reorder/`: live tracking and one-click reorder
- `desktop/smartkart_desktop.py`: **Tkinter** Store Manager Console sharing the Django ORM and database

### 9.4 Two user interfaces, one database
```
             +----------------------+          +-------------------------------+
 Customers → |  Web UI (Django DTL, |          |  Tkinter Desktop Console      | ← Store manager
 Admin     → |  Bootstrap, JS,      |          |  (ttk Notebook, Treeview,     |
 Riders    → |  Chart.js, SVG)      |          |   Canvas charts, dialogs)     |
             +----------+-----------+          +---------------+---------------+
                        |       Django ORM models (same Python code)      |
                        +--------------------+----------------------------+
                                             v
                                       db.sqlite3
```

### 9.5 Testing summary
58 automated tests (`python manage.py test`) covering all 8 apps, up from 15 in version 1. They pass on Django 5.2 LTS and Django 6.x.
