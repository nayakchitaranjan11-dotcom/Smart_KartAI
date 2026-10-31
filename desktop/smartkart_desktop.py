"""
SmartKart AI - Store Manager Desktop Console  (Tkinter)
======================================================

A desktop companion app for the SmartKart AI web project, written with Python's
built-in GUI toolkit **Tkinter** (the same toolkit used in our Python classes).

It does NOT need the web server to be running. It opens the SAME SQLite database
(db.sqlite3) through the Django ORM, so any change made here (stock, order status,
new product ...) is instantly visible on the website and vice-versa.

Run from the project root folder:

    python desktop/smartkart_desktop.py

Login with an administrator account (default:  admin / password123).

Tkinter concepts demonstrated
-----------------------------
* tk.Tk root window, Frames, grid() & pack() geometry managers
* ttk widgets: Notebook (tabs), Treeview (tables), Combobox, Spinbox, Scrollbar, Style/themes
* Entry / Text / Label / Button / Checkbutton widgets, StringVar / IntVar / BooleanVar
* Event binding (<Double-1>, <<TreeviewSelect>>, <Return>)
* Canvas drawing (bar chart built from rectangles and text, no matplotlib needed)
* Toplevel pop-up dialogs, messagebox and filedialog
* after() timer for a live clock and auto-refresh
"""

import csv
import datetime
import os
import sys
from decimal import Decimal, InvalidOperation
from pathlib import Path

import tkinter as tk
from tkinter import ttk, messagebox, filedialog

# --------------------------------------------------------------------------------------
# 1. Connect to the Django project (so we can reuse the same models & database)
# --------------------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'smartkart.settings')

import django  # noqa: E402

django.setup()

from django.contrib.auth import authenticate  # noqa: E402
from django.contrib.auth.models import User  # noqa: E402
from django.db.models import Sum, Count, Q  # noqa: E402
from django.utils import timezone  # noqa: E402

from apps.catalogue.models import Product, Category, Brand  # noqa: E402
from apps.orders.models import Order, DeliveryAssignment  # noqa: E402
from apps.smart_features.models import ExpiryRescueDeal  # noqa: E402
from apps.smart_features.expiry_service import ExpiryRescueService  # noqa: E402
from apps.orders.invoice_generator import generate_order_invoice_pdf  # noqa: E402

# --------------------------------------------------------------------------------------
# 2. Theme (same colours as the website's CSS design system)
# --------------------------------------------------------------------------------------
PRIMARY = '#0F5132'
PRIMARY_DARK = '#0B3D26'
SECONDARY = '#10B981'
ACCENT = '#EA580C'
DANGER = '#DC2626'
WARNING = '#F59E0B'
BG = '#F8FAFC'
CARD = '#FFFFFF'
TEXT = '#1E293B'
MUTED = '#64748B'
BORDER = '#E2E8F0'

FONT = ('Segoe UI', 10)
FONT_BOLD = ('Segoe UI', 10, 'bold')
FONT_H1 = (FONT[0], 18, 'bold')
FONT_H2 = ('Segoe UI', 13, 'bold')
FONT_KPI = ('Segoe UI', 20, 'bold')

ORDER_FLOW = ['PLACED', 'CONFIRMED', 'PACKING', 'READY_FOR_PICKUP', 'ASSIGNED',
              'PICKED_UP', 'OUT_FOR_DELIVERY', 'DELIVERED', 'CANCELLED']
STATUS_LABELS = dict(Order.STATUS_CHOICES)


def money(value):
    """Format a number as Indian Rupees: 1234.5 -> '₹1,234.50'"""
    return f"₹{Decimal(value or 0):,.2f}"


def pick_font_family(root):
    """Use Segoe UI on Windows, otherwise the best available sans-serif font (macOS / Linux)."""
    from tkinter import font as tkfont
    available = set(tkfont.families(root))
    for family in ('Segoe UI', 'Helvetica Neue', 'Inter', 'DejaVu Sans', 'Noto Sans', 'Liberation Sans', 'Arial', 'Helvetica'):
        if family in available:
            return family
    return 'TkDefaultFont'


def setup_styles(root):
    global FONT, FONT_BOLD, FONT_H1, FONT_H2, FONT_KPI
    family = pick_font_family(root)
    FONT, FONT_BOLD = (family, 10), (family, 10, 'bold')
    FONT_H1, FONT_H2, FONT_KPI = (family, 18, 'bold'), (family, 13, 'bold'), (family, 20, 'bold')
    root.option_add('*Font', FONT)
    style = ttk.Style(root)
    try:
        style.theme_use('clam')          # 'clam' looks the same on Windows / macOS / Linux
    except tk.TclError:
        pass
    style.configure('.', font=FONT, background=BG, foreground=TEXT)
    style.configure('TFrame', background=BG)
    style.configure('Card.TFrame', background=CARD, relief='flat')
    style.configure('TLabel', background=BG, foreground=TEXT)
    style.configure('Card.TLabel', background=CARD)
    style.configure('Muted.TLabel', background=CARD, foreground=MUTED)
    style.configure('H1.TLabel', font=FONT_H1, background=BG, foreground=PRIMARY)
    style.configure('H2.TLabel', font=FONT_H2, background=CARD, foreground=TEXT)
    style.configure('TNotebook', background=BG, borderwidth=0)
    style.configure('TNotebook.Tab', padding=(16, 8), font=FONT_BOLD)
    style.map('TNotebook.Tab', background=[('selected', CARD)], foreground=[('selected', PRIMARY)])
    style.configure('Treeview', rowheight=28, font=FONT, fieldbackground=CARD, background=CARD)
    style.configure('Treeview.Heading', font=FONT_BOLD, background='#EEF2F7', foreground=TEXT)
    style.map('Treeview', background=[('selected', '#D1FAE5')], foreground=[('selected', TEXT)])
    style.configure('Accent.TButton', background=PRIMARY, foreground='white', font=FONT_BOLD, padding=(14, 6))
    style.map('Accent.TButton', background=[('active', PRIMARY_DARK)])
    style.configure('Danger.TButton', background=DANGER, foreground='white', font=FONT_BOLD, padding=(12, 6))
    style.map('Danger.TButton', background=[('active', '#B91C1C')])
    style.configure('TButton', padding=(10, 5))
    return style


# --------------------------------------------------------------------------------------
# 3. Reusable widgets
# --------------------------------------------------------------------------------------
class KpiCard(tk.Frame):
    """A white 'card' with a title, a big number and a small caption."""

    def __init__(self, parent, title, colour=PRIMARY):
        super().__init__(parent, bg=CARD, highlightthickness=1, highlightbackground=BORDER, padx=16, pady=12)
        tk.Frame(self, bg=colour, height=4).pack(fill='x', pady=(0, 8))
        tk.Label(self, text=title.upper(), bg=CARD, fg=MUTED, font=(FONT[0], 9, 'bold')).pack(anchor='w')
        self.value = tk.Label(self, text='-', bg=CARD, fg=colour, font=FONT_KPI)
        self.value.pack(anchor='w')
        self.caption = tk.Label(self, text='', bg=CARD, fg=MUTED, font=(FONT[0], 9))
        self.caption.pack(anchor='w')

    def set(self, value, caption=''):
        self.value.config(text=value)
        self.caption.config(text=caption)


def make_tree(parent, columns, widths, height=14):
    """Create a Treeview + vertical scrollbar inside `parent`. Returns the Treeview."""
    holder = ttk.Frame(parent)
    holder.pack(fill='both', expand=True)
    tree = ttk.Treeview(holder, columns=columns, show='headings', height=height)
    for col, width in zip(columns, widths):
        tree.heading(col, text=col, command=lambda c=col: sort_tree(tree, c, False))
        tree.column(col, width=width, anchor='w', stretch=True)
    vsb = ttk.Scrollbar(holder, orient='vertical', command=tree.yview)
    tree.configure(yscrollcommand=vsb.set)
    tree.pack(side='left', fill='both', expand=True)
    vsb.pack(side='right', fill='y')
    return tree


def sort_tree(tree, col, reverse):
    """Click a column heading to sort (numbers sorted numerically, text alphabetically)."""
    def key(item):
        raw = tree.set(item, col).replace('₹', '').replace(',', '').strip()
        try:
            return (0, float(raw))
        except ValueError:
            return (1, raw.lower())
    rows = sorted(tree.get_children(''), key=key, reverse=reverse)
    for index, item in enumerate(rows):
        tree.move(item, '', index)
    tree.heading(col, command=lambda: sort_tree(tree, col, not reverse))


# --------------------------------------------------------------------------------------
# 4. Login window
# --------------------------------------------------------------------------------------
class LoginFrame(tk.Frame):
    def __init__(self, master, on_success):
        super().__init__(master, bg=BG)
        self.on_success = on_success

        card = tk.Frame(self, bg=CARD, padx=40, pady=32, highlightthickness=1, highlightbackground=BORDER)
        card.place(relx=0.5, rely=0.5, anchor='center')

        logo = tk.Canvas(card, width=64, height=64, bg=CARD, highlightthickness=0)
        logo.create_oval(4, 4, 60, 60, fill=PRIMARY, outline='')
        logo.create_text(32, 33, text='SK', fill='white', font=(FONT[0], 18, 'bold'))
        logo.pack(pady=(0, 8))

        tk.Label(card, text='SmartKart AI', bg=CARD, fg=PRIMARY, font=FONT_H1).pack()
        tk.Label(card, text='Store Manager Desktop Console', bg=CARD, fg=MUTED, font=FONT).pack(pady=(0, 18))

        self.username = tk.StringVar(value='admin')
        self.password = tk.StringVar()

        tk.Label(card, text='Admin username', bg=CARD, fg=TEXT, font=FONT_BOLD).pack(anchor='w')
        user_entry = ttk.Entry(card, textvariable=self.username, width=32)
        user_entry.pack(fill='x', pady=(2, 10))
        tk.Label(card, text='Password', bg=CARD, fg=TEXT, font=FONT_BOLD).pack(anchor='w')
        pwd_entry = ttk.Entry(card, textvariable=self.password, show='•', width=32)
        pwd_entry.pack(fill='x', pady=(2, 16))
        pwd_entry.bind('<Return>', lambda e: self.try_login())

        ttk.Button(card, text='Login', style='Accent.TButton', command=self.try_login).pack(fill='x')
        self.error = tk.Label(card, text='', bg=CARD, fg=DANGER, font=FONT)
        self.error.pack(pady=(10, 0))
        tk.Label(card, text='Demo: admin / password123', bg=CARD, fg=MUTED, font=(FONT[0], 9)).pack()
        pwd_entry.focus_set()

    def try_login(self):
        user = authenticate(username=self.username.get().strip(), password=self.password.get())
        if user is None:
            self.error.config(text='Invalid username or password')
        elif not (user.is_staff or user.is_superuser):
            self.error.config(text='Only administrators can use this console')
        else:
            self.on_success(user)


# --------------------------------------------------------------------------------------
# 5. Tabs
# --------------------------------------------------------------------------------------
class DashboardTab(ttk.Frame):
    """KPI cards + hand-drawn Canvas charts."""

    def __init__(self, master, app):
        super().__init__(master, padding=16)
        self.app = app
        cards = ttk.Frame(self)
        cards.pack(fill='x')
        self.kpi_revenue = KpiCard(cards, 'Total revenue', PRIMARY)
        self.kpi_orders = KpiCard(cards, 'Orders', '#2563EB')
        self.kpi_stock = KpiCard(cards, 'Stock alerts', ACCENT)
        self.kpi_rescue = KpiCard(cards, 'Food rescued', SECONDARY)
        for i, card in enumerate((self.kpi_revenue, self.kpi_orders, self.kpi_stock, self.kpi_rescue)):
            card.grid(row=0, column=i, sticky='nsew', padx=(0 if i == 0 else 12, 0))
            cards.columnconfigure(i, weight=1)

        charts = ttk.Frame(self)
        charts.pack(fill='both', expand=True, pady=(16, 0))
        charts.columnconfigure(0, weight=3)
        charts.columnconfigure(1, weight=2)
        charts.rowconfigure(0, weight=1)

        left = tk.Frame(charts, bg=CARD, highlightthickness=1, highlightbackground=BORDER, padx=12, pady=10)
        left.grid(row=0, column=0, sticky='nsew', padx=(0, 12))
        tk.Label(left, text='Revenue - last 7 days', bg=CARD, fg=TEXT, font=FONT_H2).pack(anchor='w')
        self.bar_canvas = tk.Canvas(left, bg=CARD, highlightthickness=0, height=260)
        self.bar_canvas.pack(fill='both', expand=True)

        right = tk.Frame(charts, bg=CARD, highlightthickness=1, highlightbackground=BORDER, padx=12, pady=10)
        right.grid(row=0, column=1, sticky='nsew')
        tk.Label(right, text='Orders by status', bg=CARD, fg=TEXT, font=FONT_H2).pack(anchor='w')
        self.status_canvas = tk.Canvas(right, bg=CARD, highlightthickness=0, height=260)
        self.status_canvas.pack(fill='both', expand=True)

        # redraw charts when the window is resized
        self.bar_canvas.bind('<Configure>', lambda e: self.draw_revenue_chart())
        self.status_canvas.bind('<Configure>', lambda e: self.draw_status_chart())
        self.revenue_data, self.status_data = [], []

    def refresh(self):
        live = Order.objects.exclude(status='CANCELLED')
        total = live.aggregate(t=Sum('grand_total'))['t'] or 0
        today = live.filter(created_at__date=timezone.localdate()).aggregate(t=Sum('grand_total'))['t'] or 0
        pending = Order.objects.exclude(status__in=['DELIVERED', 'CANCELLED']).count()
        low = Product.objects.filter(is_active=True, stock_quantity__gt=0, stock_quantity__lte=10).count()
        out = Product.objects.filter(is_active=True, stock_quantity=0).count()
        rescued = ExpiryRescueService.get_total_rescued_items_count()

        self.kpi_revenue.set(money(total), f'Today: {money(today)}')
        self.kpi_orders.set(str(Order.objects.count()), f'{pending} pending fulfilment')
        self.kpi_stock.set(f'{low + out}', f'{low} low  |  {out} out of stock')
        self.kpi_rescue.set(f'{rescued} units', 'saved from food waste')

        # last 7 days revenue
        self.revenue_data = []
        for days_ago in range(6, -1, -1):
            day = timezone.localdate() - datetime.timedelta(days=days_ago)
            amount = live.filter(created_at__date=day).aggregate(t=Sum('grand_total'))['t'] or 0
            self.revenue_data.append((day.strftime('%a\n%d'), float(amount)))
        counts = dict(Order.objects.values_list('status').annotate(c=Count('id')))
        self.status_data = [(STATUS_LABELS[s], counts.get(s, 0)) for s in ORDER_FLOW if counts.get(s, 0)]
        self.draw_revenue_chart()
        self.draw_status_chart()

    def draw_revenue_chart(self):
        c = self.bar_canvas
        c.delete('all')
        w, h = max(c.winfo_width(), 300), max(c.winfo_height(), 200)
        if not self.revenue_data:
            return
        pad_l, pad_b, pad_t = 50, 40, 20
        peak = max(v for _, v in self.revenue_data) or 1
        slot = (w - pad_l - 10) / len(self.revenue_data)
        # horizontal grid lines + axis labels
        for i in range(5):
            y = pad_t + (h - pad_t - pad_b) * i / 4
            c.create_line(pad_l, y, w - 10, y, fill='#EEF2F7')
            c.create_text(pad_l - 6, y, text=f'{peak * (4 - i) / 4:,.0f}', anchor='e', fill=MUTED, font=(FONT[0], 8))
        for i, (label, value) in enumerate(self.revenue_data):
            x0 = pad_l + i * slot + slot * 0.2
            x1 = x0 + slot * 0.6
            y1 = h - pad_b
            y0 = y1 - (h - pad_t - pad_b) * (value / peak)
            c.create_rectangle(x0, y0, x1, y1, fill=SECONDARY if i == len(self.revenue_data) - 1 else PRIMARY, outline='')
            if value:
                c.create_text((x0 + x1) / 2, y0 - 8, text=f'₹{value:,.0f}', fill=TEXT, font=(FONT[0], 8, 'bold'))
            c.create_text((x0 + x1) / 2, y1 + 16, text=label, fill=MUTED, font=(FONT[0], 8))

    def draw_status_chart(self):
        c = self.status_canvas
        c.delete('all')
        w = max(c.winfo_width(), 240)
        if not self.status_data:
            c.create_text(w / 2, 60, text='No orders yet', fill=MUTED)
            return
        peak = max(v for _, v in self.status_data) or 1
        palette = [PRIMARY, '#2563EB', SECONDARY, WARNING, ACCENT, '#7C3AED', '#0891B2', '#16A34A', DANGER]
        for i, (label, value) in enumerate(self.status_data):
            y = 14 + i * 30
            c.create_text(4, y + 9, text=label, anchor='w', fill=TEXT, font=(FONT[0], 9))
            bar_x0 = 150
            bar_len = (w - bar_x0 - 40) * value / peak
            c.create_rectangle(bar_x0, y + 2, bar_x0 + max(bar_len, 4), y + 18, fill=palette[i % len(palette)], outline='')
            c.create_text(bar_x0 + bar_len + 8, y + 10, text=str(value), anchor='w', fill=TEXT, font=(FONT[0], 9, 'bold'))


class InventoryTab(ttk.Frame):
    COLUMNS = ('ID', 'Product', 'Category', 'Unit', 'Price', 'Stock', 'Status')

    def __init__(self, master, app):
        super().__init__(master, padding=16)
        self.app = app
        bar = ttk.Frame(self)
        bar.pack(fill='x', pady=(0, 10))
        ttk.Label(bar, text='Search:').pack(side='left')
        self.search = tk.StringVar()
        entry = ttk.Entry(bar, textvariable=self.search, width=28)
        entry.pack(side='left', padx=(4, 12))
        entry.bind('<Return>', lambda e: self.refresh())
        ttk.Label(bar, text='Category:').pack(side='left')
        self.category = tk.StringVar(value='All')
        self.category_box = ttk.Combobox(bar, textvariable=self.category, state='readonly', width=24)
        self.category_box.pack(side='left', padx=(4, 12))
        self.category_box.bind('<<ComboboxSelected>>', lambda e: self.refresh())
        self.only_alerts = tk.BooleanVar()
        ttk.Checkbutton(bar, text='Only low / out of stock', variable=self.only_alerts, command=self.refresh).pack(side='left')
        ttk.Button(bar, text='Export CSV', command=self.export_csv).pack(side='right')
        ttk.Button(bar, text='Restock +10', command=lambda: self.adjust_selected(10)).pack(side='right', padx=6)
        ttk.Button(bar, text='Edit Stock / Price', style='Accent.TButton', command=self.edit_selected).pack(side='right')

        self.tree = make_tree(self, self.COLUMNS, (50, 320, 170, 80, 90, 70, 110), height=18)
        self.tree.tag_configure('out', background='#FEE2E2')
        self.tree.tag_configure('low', background='#FFEDD5')
        self.tree.tag_configure('inactive', foreground=MUTED)
        self.tree.bind('<Double-1>', lambda e: self.edit_selected())
        self.summary = ttk.Label(self, text='')
        self.summary.pack(anchor='w', pady=(8, 0))

    def refresh(self):
        cats = ['All'] + list(Category.objects.order_by('name').values_list('name', flat=True))
        self.category_box['values'] = cats
        qs = Product.objects.select_related('category').order_by('category__name', 'name')
        term = self.search.get().strip()
        if term:
            qs = qs.filter(Q(name__icontains=term) | Q(category__name__icontains=term))
        if self.category.get() not in ('', 'All'):
            qs = qs.filter(category__name=self.category.get())
        if self.only_alerts.get():
            qs = qs.filter(stock_quantity__lte=10)
        self.tree.delete(*self.tree.get_children())
        for p in qs:
            if not p.is_active:
                status, tag = 'Inactive', 'inactive'
            elif p.stock_quantity == 0:
                status, tag = 'OUT OF STOCK', 'out'
            elif p.stock_quantity <= p.reorder_level:
                status, tag = 'Low stock', 'low'
            else:
                status, tag = 'In stock', ''
            self.tree.insert('', 'end', iid=str(p.pk), tags=(tag,), values=(
                p.pk, p.name, p.category.name, p.unit, money(p.selling_price), p.stock_quantity, status))
        self.summary.config(text=f'{len(self.tree.get_children())} products shown   •   double-click a row to edit')

    def selected_product(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showinfo('Select a product', 'Please select a product in the table first.')
            return None
        return Product.objects.get(pk=int(sel[0]))

    def adjust_selected(self, delta):
        product = self.selected_product()
        if product:
            product.stock_quantity = max(0, product.stock_quantity + delta)
            product.save(update_fields=['stock_quantity'])
            self.app.set_status(f'Restocked {product.name} -> {product.stock_quantity} units')
            self.app.refresh_all()
            self.tree.selection_set(str(product.pk))

    def edit_selected(self):
        product = self.selected_product()
        if not product:
            return
        win = tk.Toplevel(self)
        win.title(f'Edit - {product.name}')
        win.configure(bg=CARD, padx=20, pady=16)
        win.transient(self.winfo_toplevel())
        win.grab_set()
        tk.Label(win, text=product.name, bg=CARD, fg=PRIMARY, font=FONT_H2, wraplength=320, justify='left').grid(row=0, column=0, columnspan=2, sticky='w', pady=(0, 12))
        stock = tk.IntVar(value=product.stock_quantity)
        price = tk.StringVar(value=str(product.selling_price))
        mrp = tk.StringVar(value=str(product.original_price))
        active = tk.BooleanVar(value=product.is_active)
        rows = [('Stock quantity', ttk.Spinbox(win, from_=0, to=10000, textvariable=stock, width=12)),
                ('Selling price (₹)', ttk.Entry(win, textvariable=price, width=14)),
                ('MRP (₹)', ttk.Entry(win, textvariable=mrp, width=14))]
        for i, (label, widget) in enumerate(rows, start=1):
            tk.Label(win, text=label, bg=CARD, font=FONT_BOLD).grid(row=i, column=0, sticky='w', pady=4)
            widget.grid(row=i, column=1, sticky='w', pady=4)
        ttk.Checkbutton(win, text='Active (visible on website)', variable=active).grid(row=4, column=0, columnspan=2, sticky='w', pady=6)

        def save():
            try:
                new_price, new_mrp = Decimal(price.get()), Decimal(mrp.get())
                new_stock = int(stock.get())
            except (InvalidOperation, ValueError, tk.TclError):
                messagebox.showerror('Invalid value', 'Please enter valid numbers.', parent=win)
                return
            if new_price <= 0 or new_mrp <= 0 or new_price > new_mrp:
                messagebox.showerror('Invalid price', 'Prices must be positive and selling price must not exceed MRP.', parent=win)
                return
            product.stock_quantity, product.selling_price, product.original_price = max(0, new_stock), new_price, new_mrp
            product.is_active = active.get()
            product.save()
            self.app.set_status(f'Saved {product.name}')
            win.destroy()
            self.app.refresh_all()

        ttk.Button(win, text='Save', style='Accent.TButton', command=save).grid(row=5, column=0, columnspan=2, sticky='ew', pady=(10, 0))

    def export_csv(self):
        path = filedialog.asksaveasfilename(defaultextension='.csv', initialfile='smartkart_inventory.csv',
                                            filetypes=[('CSV files', '*.csv')])
        if not path:
            return
        with open(path, 'w', newline='', encoding='utf-8') as fh:
            writer = csv.writer(fh)
            writer.writerow(self.COLUMNS)
            for item in self.tree.get_children():
                writer.writerow(self.tree.item(item, 'values'))
        messagebox.showinfo('Exported', f'Inventory exported to\n{path}')


class OrdersTab(ttk.Frame):
    COLUMNS = ('Order #', 'Customer', 'Items', 'Total', 'Payment', 'Status', 'Rider', 'Placed')

    def __init__(self, master, app):
        super().__init__(master, padding=16)
        self.app = app
        bar = ttk.Frame(self)
        bar.pack(fill='x', pady=(0, 10))
        ttk.Label(bar, text='Show:').pack(side='left')
        self.filter = tk.StringVar(value='Active orders')
        box = ttk.Combobox(bar, textvariable=self.filter, state='readonly', width=22,
                           values=['Active orders', 'All orders'] + [STATUS_LABELS[s] for s in ORDER_FLOW])
        box.pack(side='left', padx=6)
        box.bind('<<ComboboxSelected>>', lambda e: self.refresh())

        paned = ttk.PanedWindow(self, orient='vertical')
        paned.pack(fill='both', expand=True)
        top = ttk.Frame(paned)
        paned.add(top, weight=3)
        self.tree = make_tree(top, self.COLUMNS, (170, 150, 50, 90, 90, 150, 110, 120), height=10)
        self.tree.tag_configure('cancelled', foreground=MUTED)
        self.tree.tag_configure('delivered', foreground='#15803D')
        self.tree.bind('<<TreeviewSelect>>', lambda e: self.show_details())

        bottom = tk.Frame(paned, bg=CARD, highlightthickness=1, highlightbackground=BORDER, padx=12, pady=10)
        paned.add(bottom, weight=2)
        self.details = tk.Text(bottom, height=10, wrap='word', relief='flat', font=('Consolas', 10), bg=CARD)
        self.details.pack(side='left', fill='both', expand=True)

        actions = tk.Frame(bottom, bg=CARD, padx=12)
        actions.pack(side='right', fill='y')
        tk.Label(actions, text='Change status', bg=CARD, font=FONT_BOLD).pack(anchor='w')
        self.new_status = tk.StringVar()
        ttk.Combobox(actions, textvariable=self.new_status, state='readonly', width=24,
                     values=[STATUS_LABELS[s] for s in ORDER_FLOW]).pack(fill='x', pady=(2, 4))
        ttk.Button(actions, text='Update Status', style='Accent.TButton', command=self.update_status).pack(fill='x')
        tk.Label(actions, text='Assign delivery partner', bg=CARD, font=FONT_BOLD).pack(anchor='w', pady=(12, 0))
        self.rider = tk.StringVar()
        self.rider_box = ttk.Combobox(actions, textvariable=self.rider, state='readonly', width=24)
        self.rider_box.pack(fill='x', pady=(2, 4))
        ttk.Button(actions, text='Assign Rider', command=self.assign_rider).pack(fill='x')
        ttk.Button(actions, text='Save PDF Invoice', command=self.save_invoice).pack(fill='x', pady=(12, 0))

    def refresh(self):
        riders = User.objects.filter(delivery_profile__isnull=False).order_by('username')
        self.rider_map = {f'{r.get_full_name() or r.username} (@{r.username})': r for r in riders}
        self.rider_box['values'] = list(self.rider_map)
        qs = Order.objects.select_related('user', 'delivery_partner').prefetch_related('items').order_by('-created_at')
        choice = self.filter.get()
        if choice == 'Active orders':
            qs = qs.exclude(status__in=['DELIVERED', 'CANCELLED'])
        elif choice != 'All orders':
            code = next((k for k, v in STATUS_LABELS.items() if v == choice), None)
            qs = qs.filter(status=code)
        selected = self.tree.selection()
        self.tree.delete(*self.tree.get_children())
        for o in qs[:300]:
            tag = 'cancelled' if o.status == 'CANCELLED' else 'delivered' if o.status == 'DELIVERED' else ''
            self.tree.insert('', 'end', iid=o.order_number, tags=(tag,), values=(
                o.order_number, o.shipping_full_name, o.total_items_count, money(o.grand_total),
                o.payment_method, o.get_status_display(),
                (o.delivery_partner.get_full_name() or o.delivery_partner.username) if o.delivery_partner else '-',
                timezone.localtime(o.created_at).strftime('%d %b %H:%M')))
        if selected and self.tree.exists(selected[0]):
            self.tree.selection_set(selected[0])

    def current_order(self, quiet=False):
        sel = self.tree.selection()
        if not sel:
            if not quiet:
                messagebox.showinfo('Select an order', 'Please select an order first.')
            return None
        return Order.objects.get(order_number=sel[0])

    def show_details(self):
        order = self.current_order(quiet=True)
        self.details.delete('1.0', 'end')
        if not order:
            return
        lines = [
            f'ORDER {order.order_number}   [{order.get_status_display()}]',
            f'Customer : {order.shipping_full_name}  ({order.shipping_phone})',
            f'Address  : {order.shipping_street}, {order.shipping_city} - {order.shipping_postal_code}',
            f'Slot     : {order.get_delivery_slot_display()}',
            f'Payment  : {order.get_payment_method_display()} - {order.get_payment_status_display()}',
            '-' * 60,
        ]
        for item in order.items.all():
            lines.append(f'{item.quantity:>3} x {item.product_name[:38]:<38} {money(item.total_price):>12}')
        lines += ['-' * 60,
                  f'{"Subtotal":<44}{money(order.subtotal):>14}',
                  f'{"Discounts":<44}{"-" + money(order.total_savings):>14}',
                  f'{"Delivery fee":<44}{money(order.delivery_fee):>14}',
                  f'{"GRAND TOTAL":<44}{money(order.grand_total):>14}']
        if order.order_notes:
            lines.append(f'\nNote: {order.order_notes}')
        self.details.insert('1.0', '\n'.join(lines))
        self.new_status.set(order.get_status_display())

    def update_status(self):
        order = self.current_order()
        if not order:
            return
        code = next((k for k, v in STATUS_LABELS.items() if v == self.new_status.get()), None)
        if not code or code == order.status:
            return
        if order.status == 'CANCELLED':
            messagebox.showwarning('Not allowed', 'This order is already cancelled.')
            return
        if code == 'CANCELLED':
            if not messagebox.askyesno('Cancel order', 'Cancel this order and return all items to stock?'):
                return
            order.cancel(reason='Cancelled from desktop console', user=self.app.user)
        else:
            order.add_status_history(code, comment='Updated from SmartKart desktop console', user=self.app.user)
        self.app.set_status(f'Order {order.order_number} -> {STATUS_LABELS[code]}')
        self.app.refresh_all()

    def assign_rider(self):
        order = self.current_order()
        rider = self.rider_map.get(self.rider.get()) if order else None
        if not order:
            return
        if not rider:
            messagebox.showinfo('Choose a rider', 'Please choose a delivery partner from the list.')
            return
        if order.status in ('DELIVERED', 'CANCELLED'):
            messagebox.showwarning('Not allowed', 'This order is already closed.')
            return
        order.delivery_partner = rider
        order.save(update_fields=['delivery_partner'])
        DeliveryAssignment.objects.update_or_create(order=order, defaults={'delivery_person': rider, 'status': 'ACCEPTED'})
        order.add_status_history('ASSIGNED', comment=f'Assigned to {rider.username} from desktop console', user=self.app.user)
        self.app.set_status(f'{order.order_number} assigned to {rider.username}')
        self.app.refresh_all()

    def save_invoice(self):
        order = self.current_order()
        if not order:
            return
        path = filedialog.asksaveasfilename(defaultextension='.pdf', initialfile=f'Invoice_{order.order_number}.pdf',
                                            filetypes=[('PDF files', '*.pdf')])
        if path:
            response = generate_order_invoice_pdf(order)     # same ReportLab generator the website uses
            Path(path).write_bytes(response.content)
            messagebox.showinfo('Invoice saved', f'Invoice saved to\n{path}')


class AddProductTab(ttk.Frame):
    def __init__(self, master, app):
        super().__init__(master, padding=16)
        self.app = app
        card = tk.Frame(self, bg=CARD, highlightthickness=1, highlightbackground=BORDER, padx=24, pady=18)
        card.pack(anchor='nw', fill='x')
        tk.Label(card, text='Add a new product to the catalogue', bg=CARD, fg=PRIMARY, font=FONT_H2).grid(row=0, column=0, columnspan=4, sticky='w', pady=(0, 12))

        self.vars = {k: tk.StringVar() for k in ('name', 'category', 'brand', 'unit', 'mrp', 'price', 'stock', 'expiry', 'tags')}
        self.vars['unit'].set('1 kg')
        self.vars['stock'].set('50')
        self.featured = tk.BooleanVar()
        fields = [
            ('Product name *', ttk.Entry(card, textvariable=self.vars['name'], width=40)),
            ('Category *', ttk.Combobox(card, textvariable=self.vars['category'], state='readonly', width=37)),
            ('Brand', ttk.Combobox(card, textvariable=self.vars['brand'], width=37)),
            ('Pack size / unit *', ttk.Entry(card, textvariable=self.vars['unit'], width=20)),
            ('MRP (₹) *', ttk.Entry(card, textvariable=self.vars['mrp'], width=20)),
            ('Selling price (₹) *', ttk.Entry(card, textvariable=self.vars['price'], width=20)),
            ('Opening stock *', ttk.Spinbox(card, from_=0, to=10000, textvariable=self.vars['stock'], width=18)),
            ('Expiry date (YYYY-MM-DD)', ttk.Entry(card, textvariable=self.vars['expiry'], width=20)),
            ('Nutrition tags (comma separated)', ttk.Entry(card, textvariable=self.vars['tags'], width=40)),
        ]
        self.category_box, self.brand_box = fields[1][1], fields[2][1]
        for i, (label, widget) in enumerate(fields, start=1):
            tk.Label(card, text=label, bg=CARD, font=FONT_BOLD).grid(row=i, column=0, sticky='w', pady=5, padx=(0, 16))
            widget.grid(row=i, column=1, sticky='w', pady=5)
        tk.Label(card, text='Description', bg=CARD, font=FONT_BOLD).grid(row=10, column=0, sticky='nw', pady=5)
        self.description = tk.Text(card, height=4, width=50, font=FONT, relief='solid', bd=1)
        self.description.grid(row=10, column=1, sticky='w', pady=5)
        ttk.Checkbutton(card, text='Feature this product on the home page', variable=self.featured).grid(row=11, column=1, sticky='w', pady=6)
        ttk.Button(card, text='Save Product', style='Accent.TButton', command=self.save).grid(row=12, column=1, sticky='w', pady=(8, 0))

    def refresh(self):
        self.category_box['values'] = list(Category.objects.order_by('name').values_list('name', flat=True))
        self.brand_box['values'] = [''] + list(Brand.objects.order_by('name').values_list('name', flat=True))

    def save(self):
        v = {k: var.get().strip() for k, var in self.vars.items()}
        if not v['name'] or not v['category'] or not v['unit']:
            messagebox.showerror('Missing data', 'Name, category and unit are required.')
            return
        try:
            mrp, price, stock = Decimal(v['mrp']), Decimal(v['price']), int(v['stock'])
        except (InvalidOperation, ValueError):
            messagebox.showerror('Invalid number', 'MRP, selling price and stock must be numbers.')
            return
        if price <= 0 or mrp <= 0 or price > mrp:
            messagebox.showerror('Invalid price', 'Prices must be positive and selling price must not exceed MRP.')
            return
        expiry = None
        if v['expiry']:
            try:
                expiry = datetime.date.fromisoformat(v['expiry'])
            except ValueError:
                messagebox.showerror('Invalid date', 'Expiry date must look like 2026-12-31.')
                return
        brand = None
        if v['brand']:
            brand, _ = Brand.objects.get_or_create(name=v['brand'])
        product = Product.objects.create(
            name=v['name'], category=Category.objects.get(name=v['category']), brand=brand,
            description=self.description.get('1.0', 'end').strip() or v['name'],
            original_price=mrp, selling_price=price, unit=v['unit'], stock_quantity=max(0, stock),
            expiry_date=expiry, nutritional_tags=v['tags'], is_featured=self.featured.get(),
        )
        messagebox.showinfo('Product added', f"'{product.name}' is now live on the website.")
        for key in ('name', 'mrp', 'price', 'expiry', 'tags'):
            self.vars[key].set('')
        self.description.delete('1.0', 'end')
        self.app.set_status(f'Added product {product.name}')
        self.app.refresh_all()


class AlertsTab(ttk.Frame):
    COLUMNS = ('Product', 'Alert', 'Detail', 'Stock')

    def __init__(self, master, app):
        super().__init__(master, padding=16)
        self.app = app
        bar = ttk.Frame(self)
        bar.pack(fill='x', pady=(0, 10))
        ttk.Label(bar, text='Low stock and near-expiry items that need attention').pack(side='left')
        ttk.Button(bar, text='Create 50% Rescue Deal', style='Danger.TButton', command=self.create_deal).pack(side='right')
        ttk.Button(bar, text='Restock +25', command=self.restock).pack(side='right', padx=6)
        self.tree = make_tree(self, self.COLUMNS, (340, 160, 260, 80), height=18)
        self.tree.tag_configure('expired', background='#FEE2E2')
        self.tree.tag_configure('critical', background='#FFEDD5')
        self.tree.tag_configure('warning', background='#FEF9C3')
        self.tree.tag_configure('stock', background='#E0F2FE')

    def refresh(self):
        self.tree.delete(*self.tree.get_children())
        alerts = ExpiryRescueService.get_admin_expiry_alerts()
        today = timezone.localdate()
        for level, label in (('expired', 'EXPIRED'), ('critical', 'Expires in <= 3 days'), ('warning', 'Expires in <= 7 days')):
            for p in alerts[level]:
                deal = ' | rescue deal active' if hasattr(p, 'expiry_deal') and p.expiry_deal.is_active else ''
                self.tree.insert('', 'end', iid=f'e{p.pk}', tags=(level,), values=(
                    p.name, label, f'Expiry {p.expiry_date:%d %b %Y} ({(p.expiry_date - today).days} d){deal}', p.stock_quantity))
        for p in Product.objects.filter(is_active=True, stock_quantity__lte=10).order_by('stock_quantity'):
            if not self.tree.exists(f's{p.pk}'):
                self.tree.insert('', 'end', iid=f's{p.pk}', tags=('stock',), values=(
                    p.name, 'Out of stock' if p.stock_quantity == 0 else 'Low stock', f'Reorder level {p.reorder_level}', p.stock_quantity))

    def _selected(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showinfo('Select an item', 'Please select an alert row first.')
            return None
        return Product.objects.get(pk=int(sel[0][1:]))

    def restock(self):
        p = self._selected()
        if p:
            p.stock_quantity += 25
            p.save(update_fields=['stock_quantity'])
            self.app.set_status(f'Restocked {p.name}')
            self.app.refresh_all()

    def create_deal(self):
        p = self._selected()
        if not p:
            return
        if not p.expiry_date or p.expiry_date < timezone.localdate():
            messagebox.showwarning('Not possible', 'Rescue deals need a product with a future expiry date.')
            return
        deal, _ = ExpiryRescueDeal.objects.update_or_create(product=p, defaults={
            'rescue_discount_percent': 50, 'rescue_price': Decimal('0'), 'expiry_date': p.expiry_date,
            'start_date': timezone.localdate(), 'end_date': p.expiry_date, 'is_active': True})
        from apps.core.notifications import notify_wishlist_rescue_deal
        notify_wishlist_rescue_deal(deal)
        messagebox.showinfo('Rescue deal live', f'{p.name} now sells at {money(deal.rescue_price)} (50% off MRP).')
        self.app.refresh_all()


# --------------------------------------------------------------------------------------
# 6. Main application window
# --------------------------------------------------------------------------------------
class SmartKartDesktop(tk.Tk):
    REFRESH_MS = 30_000   # auto refresh every 30 seconds (picks up new website orders)

    def __init__(self):
        super().__init__()
        self.title('SmartKart AI - Store Manager Console')
        self.geometry('1200x760')
        self.minsize(1000, 640)
        self.configure(bg=BG)
        setup_styles(self)
        self.user = None
        self.login = LoginFrame(self, self.on_login)
        self.login.pack(fill='both', expand=True)

    def on_login(self, user):
        self.user = user
        self.login.destroy()

        header = tk.Frame(self, bg=PRIMARY, padx=18, pady=10)
        header.pack(fill='x')
        tk.Label(header, text='SmartKart AI', bg=PRIMARY, fg='white', font=FONT_H1).pack(side='left')
        tk.Label(header, text='  Store Manager Console', bg=PRIMARY, fg='#A7F3D0', font=FONT_H2).pack(side='left')
        ttk.Button(header, text='Refresh', command=self.refresh_all).pack(side='right')
        self.clock = tk.Label(header, bg=PRIMARY, fg='white', font=FONT)
        self.clock.pack(side='right', padx=16)
        tk.Label(header, text=f'Logged in as {user.get_full_name() or user.username}', bg=PRIMARY, fg='white', font=FONT).pack(side='right')

        notebook = ttk.Notebook(self)
        notebook.pack(fill='both', expand=True, padx=12, pady=12)
        self.tabs = [
            ('Dashboard', DashboardTab(notebook, self)),
            ('Inventory', InventoryTab(notebook, self)),
            ('Orders', OrdersTab(notebook, self)),
            ('Add Product', AddProductTab(notebook, self)),
            ('Alerts', AlertsTab(notebook, self)),
        ]
        for title, tab in self.tabs:
            notebook.add(tab, text=title)

        self.status = tk.Label(self, text='Ready', anchor='w', bg='#E2E8F0', fg=TEXT, padx=10, pady=4, font=(FONT[0], 9))
        self.status.pack(fill='x', side='bottom')
        self.refresh_all()
        self.tick()
        self.after(self.REFRESH_MS, self.auto_refresh)

    def set_status(self, text):
        self.status.config(text=f'{timezone.localtime():%H:%M:%S}  -  {text}')

    def refresh_all(self):
        for _, tab in self.tabs:
            tab.refresh()

    def auto_refresh(self):
        self.refresh_all()
        self.after(self.REFRESH_MS, self.auto_refresh)

    def tick(self):
        self.clock.config(text=timezone.localtime().strftime('%a %d %b  %I:%M:%S %p'))
        self.after(1000, self.tick)


if __name__ == '__main__':
    SmartKartDesktop().mainloop()
