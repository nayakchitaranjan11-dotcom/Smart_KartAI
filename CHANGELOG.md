# SmartKart AI — Changelog

## Version 2.0: project completed and extended

Nothing was removed. Every original page, model, feature and file is still here. This version **fixes** what was broken, **finishes** what was half-built, and **adds** new features.

### 1. Bug fixes (pages and actions that crashed or misbehaved)

| # | Problem | Fix | File(s) |
|---|---|---|---|
| 1 | **All Products page crashed** (`Invalid filter: 'make_list_split'`). This broke the *Shop*, *All Products* and *Smart Substitution* links. | Added the missing `{% load core_tags %}` | `templates/catalogue/product_list.html` |
| 2 | **Sort by "Biggest Discount" crashed** (`FieldError: discount_percentage`) | Sorting now uses a database expression `(MRP − price) / MRP` (cast to float for SQLite) | `apps/catalogue/views.py` |
| 3 | **Saving the monthly budget always failed** (`name 'timezone' is not defined`) | Added the missing import | `apps/smart_features/views.py` |
| 4 | `MonthlyBudget` month/year defaults were frozen when the server started, so a new migration appeared every month | They are now functions (`current_month`, `current_year`), with migration `0002` | `apps/smart_features/models.py` |
| 5 | **Order tracking highlighted the wrong step.** At "Picked Up" it showed "Delivered" because the two status lists had different lengths | Each status is mapped to its timeline step, and a "Delivery Partner Assigned" step was added | `apps/orders/views.py` |
| 6 | Admin "Cancelled" status did **not** return stock | New `Order.cancel()`, used by both the customer and admin cancel paths; it also marks prepaid UPI/Card payments **REFUNDED** | `apps/orders/models.py` |
| 7 | Recipe servings (2/4/6/8) changed the numbers on screen but **always added 1 pack** to the cart | New unit converter works out the real pack count (e.g. 1.2 kg needed → 2 × 1 kg packs) | `apps/smart_features/units.py`, `recipe_service.py` |
| 8 | Coupons created in the admin had naive dates (timezone warning) | The date is made timezone-aware, and duplicate codes are refused | `apps/dashboard/views.py` |
| 9 | Login `?next=` could redirect to another website (open-redirect security issue) | Uses Django's `url_has_allowed_host_and_scheme` | `apps/accounts/views.py` |
| 10 | Checkout accepted any delivery-slot or payment value from the form | Values are checked against the allowed choices | `apps/orders/views.py` |
| 11 | Notifications page marked items as read *before* showing them, so nothing was ever highlighted | The list is loaded first, then marked as read | `apps/core/views.py` |
| 12 | Rider status comment showed the *old* status name | Uses the new status name | `apps/delivery/views.py` |
| 13 | `apps/accounts/performance_auditor.py` could not run (all indentation lost, Markdown ``` fences inside) | Indentation restored and fences removed; it now runs as a standalone script (it is not used by the web app) | `apps/accounts/performance_auditor.py` |
| 14 | Header buttons wrapped onto two lines; category pills ran under "All Products" | CSS fixes | `static/css/main.css` |
| 15 | Site broke without internet (Bootstrap, icons and Chart.js came from a CDN) | Copies stored locally in `static/vendor/` | `templates/base.html` |
| 16 | Admin and Budget dashboards drew every chart **twice** (JavaScript error "Canvas is already in use") | `{% block extra_js %}` was nested inside `{% block content %}`, so Django rendered it twice. It is now outside | `admin_dashboard.html`, `budget_dashboard.html` |
| 17 | Admin 6-month revenue chart showed the same month twice (e.g. "Oct, Oct" on the 31st) and skipped one | Steps back by real calendar months, not 30-day jumps | `apps/dashboard/views.py` |
| 18 | Demo data went stale: weeks after seeding, milk, paneer and tomatoes were locked as *expired* | New `python manage.py seed_data --refresh-dates` moves demo expiry dates forward (the shipped database is already refreshed) | `seed_data.py` |

### 2. Unfinished parts completed

- **Django admin (`/admin/`)**: every model is now registered, with search, filters, inline order items and recipe ingredients. Before, all eight `admin.py` files were empty.
- **Notification engine** (`apps/core/notifications.py`): the Notification model existed, but nothing ever created a notification. It now sends:
  - order placed and every status change (customer)
  - new delivery assigned (rider)
  - monthly budget warning and limit exceeded (at most once each per month)
  - wishlisted item now on an Expiry Rescue deal
  - welcome message on sign-up

  There is also a 🔔 **bell with an unread count** in the navbar.
- **Admin dashboard CRUD**: Recipes can now be **added, edited and deleted** with ingredient rows (before, they could only be listed). Categories can be **edited**, coupons **paused or activated**, rescue deals **deactivated or reactivated**, riders set **on or off duty**, and there is a new **Support Inbox** for Contact-Us messages.
- **Tests**: grew from **15 to 58** automated tests. The accounts, core, dashboard and delivery apps had *no* tests before.

### 3. New features (Blinkit-style)

| Feature | What the user sees | Code |
|---|---|---|
| **Instant cart stepper** | ADD → **[ − 1 + ]** on every product card, with no page reload | `cart/api/state/`, `cart/api/set/`, `static/js/main.js` |
| **Floating cart bar** | "3 items • ₹625 — View Cart ›", plus a free-delivery hint | `templates/base.html` |
| **Live tracking map** | Animated SVG route with a moving rider 🛵, ETA countdown and auto-refresh every 10 s | `orders/<id>/status.json`, `order_tracking.html` |
| **Rider route card** | Route preview, "Open in Maps" link, *Collect ₹X cash* hint for COD orders | `templates/delivery/order_detail.html` |
| **Order Again** | One click re-adds a past order (skips out-of-stock items) | `orders/<id>/reorder/` |
| **Buy Again strip** | Home page row of your most-bought products | `RecommendationEngine.buy_again` |
| **Frequently Bought Together** | Market-basket analysis (support/confidence), with recipe co-ingredients as a fallback | `apps/smart_features/recommendation_engine.py` |
| **Product visuals** | Emoji tiles on category colours instead of the same grey bag icon | `product_emoji` / `product_tile_color` filters |
| **Voice search** | 🎤 in the search bar (Web Speech API, Chrome/Edge) | `static/js/main.js` |
| **Recipe pack calculator** | "×2 packs = ₹170" for each ingredient, and an accurate total cost | `units.py`, `recipe_detail.html` |
| **Tkinter Store Manager Console** | Desktop app: dashboard with Canvas charts, inventory, orders, add product, alerts | `desktop/smartkart_desktop.py` |
| **Offline assets** | Runs with no internet connection | `static/vendor/` |

### 4. New documentation

- `UI_UX_GUIDE.md`: which UI tools are used and why, a Tkinter ↔ Web comparison, UX decisions, and viva Q&A
- `CHANGELOG.md`: this file
- `README.md` and `PROJECT_REPORT_NOTES.md`: updated with the new modules (original text kept)
