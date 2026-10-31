# SmartKart AI — UI / UX Guide

### Which tools build the screens, and how they compare with Tkinter

Our class used **Tkinter** for GUIs. SmartKart AI is a *Blinkit-style online grocery store*, and that kind of app has to open in a web browser on phones and laptops. So the main shop uses **web UI tools**, driven by Python and Django. The project also has a **Tkinter desktop app** (the Store Manager Console), so the Tkinter we learned in class is used too.

| Part of the project | Who uses it | UI technology |
|---|---|---|
| Customer shop, Admin portal, Delivery Partner portal | Customers, admin, riders | **Django Templates + HTML5 + CSS3 + Bootstrap 5 + JavaScript + Chart.js** (runs in a browser) |
| Store Manager Desktop Console (`desktop/smartkart_desktop.py`) | Store manager / admin | **Tkinter + ttk** (Python's built-in GUI toolkit) |

Both parts read and write the **same database** through the **same Django models**, so a change made in one shows up in the other. For example, if you restock milk in the Tkinter app, the website shows it as in stock straight away.

---

## 1. The tools used in the web UI (and what each one does)

| Tool | Version | Role in SmartKart AI | Where to find it |
|---|---|---|---|
| **Django Template Language (DTL)** | Django 5.x / 6.x | Python-side templating: `{% for product in products %}`, `{% if user.is_authenticated %}`, `{{ product.name }}`, template inheritance (`{% extends 'base.html' %}`), custom filters such as `product_emoji` | `templates/`, `apps/core/templatetags/core_tags.py` |
| **HTML5** | — | Page structure: header, nav, forms, tables, `<svg>` for the tracking map | `templates/**/*.html` |
| **CSS3 (custom design system)** | — | Brand colours (emerald `#0F5132`, lime `#10B981`, orange `#EA580C`), cards, product tiles, stepper buttons, floating cart bar, animations | `static/css/main.css` |
| **Bootstrap 5.3** | 5.3.3 | Responsive 12-column grid, utility classes (`d-flex`, `mb-3`), dropdowns, alerts, modals. Makes every page work on mobile | `static/vendor/bootstrap/` |
| **Bootstrap Icons** | 1.11.3 | 2,000+ vector icons (`bi-cart4`, `bi-bell`, `bi-bicycle`) | `static/vendor/bootstrap-icons/` |
| **Inter font** | — | Clean, modern typeface (same style as Blinkit and Zepto) | `static/vendor/inter/` |
| **Vanilla JavaScript (ES6)** | — | Live search suggestions, AJAX wishlist, **ADD → [− 1 +] stepper**, floating cart bar, toasts, live tracking map, voice search | `static/js/main.js`, small scripts inside templates |
| **Chart.js** | 4.4 | Budget donut chart, admin revenue line chart and order-status chart | `static/vendor/chartjs/` |
| **SVG** | — | Animated delivery route map (store → rider → home) | `templates/orders/order_tracking.html` |
| **Web Speech API** | browser built-in | 🎤 voice search in the search bar (Chrome / Edge) | `static/js/main.js` |
| **Emoji product tiles** | Unicode | The catalogue has no product photos, so each product shows a matching emoji (🥛 🍅 🧀) on a colour tile for its category | `core_tags.py` → `product_emoji` filter |

> **Works offline:** Bootstrap, the icons, Chart.js and the Inter font are saved in `static/vendor/`, so the whole site runs **without internet** during a lab demo or viva. (Earlier the project loaded them from a CDN, and the pages broke with no internet.)

### How a page is produced (Django MVT pattern)

```
Browser ──HTTP request──▶ urls.py ──▶ views.py (Python logic, ORM queries)
                                         │
                                         ▼
                              template.html (DTL fills in data)
                                         │
Browser ◀──── HTML + CSS + JS ───────────┘
   │
   └── JavaScript fetch() ──▶ small JSON APIs (cart stepper, tracking status, search suggestions)
```

---

## 2. Tkinter ↔ Web: the same ideas with different tools

If you know Tkinter, every web UI idea has a direct partner. Use this table to explain the project in your viva.

| Tkinter (class) | Web equivalent in SmartKart AI | Example in project |
|---|---|---|
| `root = tk.Tk()` main window | `base.html` master layout that every page `extends` | `templates/base.html` |
| `Frame` | `<div class="card">` / Bootstrap container | product cards, dashboard cards |
| `Label` | `<h3>`, `<p>`, `<span>` | prices, product names |
| `Entry` | `<input type="text">` | search bar, login form |
| `Text` | `<textarea>` | AI List Scanner manual text box |
| `Button(command=func)` | `<button>` + JavaScript `addEventListener('click', …)` or a form `POST` to a Django view | ADD / − / + buttons |
| `Checkbutton`, `Radiobutton` | `<input type="checkbox">`, `<input type="radio">` | recipe pantry checklist, payment method |
| `ttk.Combobox` | `<select>` | sort-by menu, delivery slot |
| `ttk.Treeview` (table) | `<table class="table">` | admin orders / inventory lists |
| `ttk.Notebook` (tabs) | navigation pills / pages | admin dashboard pill bar |
| `Canvas` drawing | `<svg>` + Chart.js `<canvas>` | tracking map, budget charts |
| `messagebox.showinfo()` | Bootstrap alerts (Django `messages`) and toasts | "Added to cart", "Order placed" |
| `Toplevel` pop-up | Bootstrap modal / separate page | confirm cancellation |
| `grid()` / `pack()` | Bootstrap grid (`row`, `col-md-4`) and CSS flexbox | responsive layouts |
| `StringVar` / `IntVar` | form field values / DOM element values | quantity input |
| `widget.bind('<Return>', f)` | `input.addEventListener('keyup', f)` | live search suggestions |
| `root.after(1000, f)` | `setInterval(f, 10000)` | live tracking auto-refresh |
| Single user on one PC | Many users at once, each with their own login, cart and session | customer / admin / rider roles |

**Why not Tkinter for the whole shop?** A grocery store has to run on customers' **phones** and be used by **many people at once** (customers, admin, riders), each with their own login. Tkinter apps run on one desktop for one user. A web UI covers all of that and still uses **Python (Django)** for every piece of logic. Tkinter is the right tool for the **in-store manager console**, so that is where we used it.

---

## 3. The Tkinter Store Manager Console (desktop app)

**Run it** (from the project folder, with the virtual environment active):

```bash
python desktop/smartkart_desktop.py        # Windows users can also double-click desktop/run_desktop.bat
```

Log in with `admin` / `password123`. Python's Windows and macOS installers already include Tkinter, so nothing extra needs installing.

| Tab | What it does | Tkinter concepts shown |
|---|---|---|
| **Login** | Checks the admin password with Django's `authenticate()` | `Frame`, `Entry(show='•')`, `Canvas` logo, `<Return>` key binding |
| **Dashboard** | Revenue / orders / stock / rescue KPI cards, a 7-day revenue bar chart and an orders-by-status chart | Custom `KpiCard(tk.Frame)` class, **Canvas drawing** with `create_rectangle` and `create_text` (no matplotlib) |
| **Inventory** | Search, filter by category, colour-coded low/out-of-stock rows, double-click to edit stock or price, Restock +10, Export CSV | `ttk.Treeview` + `Scrollbar`, row `tags`, `Toplevel` dialog, `Spinbox`, `filedialog` |
| **Orders** | Order list, receipt-style details, change status, assign a delivery rider, save the PDF invoice | `PanedWindow`, `<<TreeviewSelect>>` event, `Text` widget, `Combobox` |
| **Add Product** | Form with validation (price ≤ MRP, date format); the new product appears on the website at once | `StringVar`, `BooleanVar`, `Checkbutton`, `messagebox` |
| **Alerts** | Expired, near-expiry and low-stock items; one-click 50% Expiry Rescue Deal | Treeview tags, calls the same `ExpiryRescueService` the website uses |

Also: a live clock in the header and auto-refresh every 30 seconds (both use `after()`), the `clam` ttk theme styled in the website's colours, and column sorting when you click a heading.

---

## 4. UX design decisions (why the screens look the way they do)

These follow Blinkit's and Zepto's quick-commerce UX patterns:

1. **Speed is the message.** "Delivery in 15 mins", the express slot and an ETA chip on tracking all tell the user the order is quick.
2. **One-tap add.** The **ADD** button turns into a green **[ − 1 + ]** stepper *without reloading the page* (AJAX through `/cart/api/set/`).
3. **The cart is always in view.** A floating **"N items • ₹total — View Cart ›"** bar follows you down every shopping page and shows how far you are from **free delivery** (₹499).
4. **Visual products.** Every product has a colourful emoji tile, so people scan by picture, not by reading.
5. **Status you can see.** The live tracking page has an animated rider 🛵 moving from store 🏪 to home 🏠, a step-by-step timeline, and checks for updates every 10 seconds.
6. **Proactive help.** The 🔔 bell collects order updates, budget alerts (at your warning % and at 100%) and "your wishlisted item is now on a rescue deal".
7. **Smart suggestions.** "Frequently Bought Together" (association rules), **Buy Again** on the home page, Money-Saver swaps, and substitutes when an item is out of stock.
8. **Less typing.** AI List Scanner, voice search 🎤, one-click **Order Again**, and Recipe-to-Cart with automatic pack counts.
9. **Mobile first.** A bottom navigation bar on phones and Bootstrap's responsive grid; buttons are big enough to tap easily.
10. **Feedback every time.** Every action shows a toast or alert, and errors explain what to do next (for example, "only 3 left", or a link to substitutes).

### Colour system

| Token | Hex | Used for |
|---|---|---|
| Primary (Emerald) | `#0F5132` | brand, primary buttons, stepper, floating cart |
| Secondary (Lime) | `#10B981` | success, progress, route line |
| Accent (Orange) | `#EA580C` | discounts, rescue deals, home marker |
| Dark text | `#1E293B` | headings, body text |
| Muted | `#64748B` | captions |
| Background | `#F8FAFC` | page background |

---

## 5. Likely viva questions (with short answers)

- **Q: Which tool did you use for the UI and why not Tkinter?**
  The customer, admin and rider portals use **Django templates with HTML, CSS, Bootstrap and JavaScript**, because a delivery app must open in a browser on any phone and serve many users at once. Python (Django) still runs all the logic. We also built a **Tkinter Store Manager console** for the shop's back office, which shares the same database.
- **Q: How does the ADD button update without reloading?**
  JavaScript `fetch()` POSTs `product_id` and `quantity` to the Django view `cart_set_quantity_api`. That view returns JSON, and the script swaps the button for a stepper and updates the cart badge.
- **Q: How does the tracking page update by itself?**
  Every 10 seconds `setInterval` calls `/orders/<id>/status.json`. If the status has changed, the page reloads, and the rider marker moves along the SVG path with `getPointAtLength()`.
- **Q: How does the Tkinter app talk to the website's data?**
  It calls `django.setup()` with the project's settings and then uses the same ORM models (`Product`, `Order`, …) on `db.sqlite3`. No separate database or API is needed.
- **Q: How are charts drawn in Tkinter without matplotlib?**
  On a `tk.Canvas`: each bar is a `create_rectangle`, with a height scaled to the largest value, and the labels are `create_text`.
