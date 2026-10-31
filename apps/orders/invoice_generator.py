"""
SmartKart AI Invoice Generator using ReportLab
---------------------------------------------
Generates downloadable, professional PDF tax invoices for customer orders
with item snapshots, pricing, discounts, delivery info, and academic project disclaimers.
"""

from io import BytesIO
from django.http import HttpResponse
from django.utils import timezone
from decimal import Decimal

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.units import inch
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable


def generate_order_invoice_pdf(order):
    """
    Builds and returns a PDF binary HttpResponse for the specified order.
    """
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=36,
        leftMargin=36,
        topMargin=36,
        bottomMargin=36
    )

    styles = getSampleStyleSheet()
    
    # Custom styles
    primary_color = colors.HexColor('#0F5132')
    secondary_color = colors.HexColor('#10B981')
    dark_color = colors.HexColor('#1F2937')
    light_bg = colors.HexColor('#F8FAFC')
    border_color = colors.HexColor('#E2E8F0')

    title_style = ParagraphStyle(
        'InvoiceTitle',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=20,
        leading=24,
        textColor=primary_color,
    )

    subtitle_style = ParagraphStyle(
        'InvoiceSubtitle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        leading=12,
        textColor=colors.HexColor('#64748B'),
    )

    heading_style = ParagraphStyle(
        'SectionHeading',
        parent=styles['Heading3'],
        fontName='Helvetica-Bold',
        fontSize=11,
        leading=14,
        textColor=primary_color,
    )

    normal_style = ParagraphStyle(
        'InvoiceNormal',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        leading=13,
        textColor=dark_color,
    )

    bold_style = ParagraphStyle(
        'InvoiceBold',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=9,
        leading=13,
        textColor=dark_color,
    )

    story = []

    # 1. Header Table (Company Branding & Invoice Meta)
    header_data = [
        [
            Paragraph("<b>SmartKart AI</b><br/><font size='8' color='#10B981'>Intelligent Quick Commerce</font>", title_style),
            Paragraph(f"<b>TAX INVOICE</b><br/><b>Invoice #:</b> INV-{order.order_number}<br/><b>Order Date:</b> {order.created_at.strftime('%d %b %Y, %I:%M %p')}<br/><b>Status:</b> {order.get_status_display()}", normal_style)
        ]
    ]
    header_table = Table(header_data, colWidths=[280, 240])
    header_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('ALIGN', (1, 0), (1, 0), 'RIGHT'),
    ]))
    story.append(header_table)
    story.append(Spacer(1, 12))
    story.append(HRFlowable(width="100%", thickness=1, color=primary_color, spaceAfter=12))

    # 2. Customer & Delivery Information
    info_data = [
        [
            Paragraph("<b>BILLED & DELIVERED TO:</b>", heading_style),
            Paragraph("<b>DELIVERY & PAYMENT DETAILS:</b>", heading_style),
        ],
        [
            Paragraph(
                f"<b>{order.shipping_full_name}</b><br/>"
                f"Phone: {order.shipping_phone}<br/>"
                f"{order.shipping_street}<br/>"
                f"{order.shipping_landmark + ', ' if order.shipping_landmark else ''}{order.shipping_city}, {order.shipping_state} - {order.shipping_postal_code}",
                normal_style
            ),
            Paragraph(
                f"<b>Delivery Slot:</b> {order.get_delivery_slot_display()}<br/>"
                f"<b>Payment Method:</b> {order.get_payment_method_display()}<br/>"
                f"<b>Payment Status:</b> {order.get_payment_status_display()}<br/>"
                f"<b>Transaction Ref:</b> {order.transaction_id or 'COD-SIMULATED'}",
                normal_style
            ),
        ]
    ]
    info_table = Table(info_data, colWidths=[280, 240])
    info_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('BACKGROUND', (0, 0), (-1, -1), light_bg),
        ('PADDING', (0, 0), (-1, -1), 8),
        ('BOX', (0, 0), (-1, -1), 0.5, border_color),
    ]))
    story.append(info_table)
    story.append(Spacer(1, 15))

    # 3. Items Table
    items_header = [
        Paragraph("<b>#</b>", bold_style),
        Paragraph("<b>Item Description</b>", bold_style),
        Paragraph("<b>Pack/Unit</b>", bold_style),
        Paragraph("<b>Unit Price</b>", bold_style),
        Paragraph("<b>Qty</b>", bold_style),
        Paragraph("<b>Total (INR)</b>", bold_style),
    ]
    table_rows = [items_header]

    for idx, item in enumerate(order.items.all(), 1):
        table_rows.append([
            Paragraph(str(idx), normal_style),
            Paragraph(item.product_name, normal_style),
            Paragraph(item.product_unit, normal_style),
            Paragraph(f"Rs. {item.unit_price}", normal_style),
            Paragraph(str(item.quantity), normal_style),
            Paragraph(f"Rs. {item.total_price}", bold_style),
        ])

    items_table = Table(table_rows, colWidths=[25, 235, 75, 65, 35, 85])
    items_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#E6F4EA')),
        ('TEXTCOLOR', (0, 0), (-1, 0), primary_color),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('GRID', (0, 0), (-1, -1), 0.5, border_color),
        ('ALIGN', (0, 0), (0, -1), 'CENTER'),
        ('ALIGN', (3, 0), (-1, -1), 'RIGHT'),
    ]))
    story.append(items_table)
    story.append(Spacer(1, 10))

    # 4. Calculation Summary Table
    summary_data = [
        [Paragraph("", normal_style), Paragraph("<b>Items Subtotal:</b>", normal_style), Paragraph(f"Rs. {order.subtotal}", normal_style)],
        [Paragraph("", normal_style), Paragraph("<b>Product Discounts:</b>", normal_style), Paragraph(f"- Rs. {order.product_discount}", normal_style)],
    ]
    if order.coupon_code:
        summary_data.append([
            Paragraph("", normal_style),
            Paragraph(f"<b>Coupon ({order.coupon_code}):</b>", normal_style),
            Paragraph(f"- Rs. {order.coupon_discount}", normal_style)
        ])
    summary_data.extend([
        [Paragraph("", normal_style), Paragraph("<b>Delivery Charges:</b>", normal_style), Paragraph(f"Rs. {order.delivery_fee}", normal_style)],
        [Paragraph("", normal_style), Paragraph("<b>Grand Total:</b>", bold_style), Paragraph(f"<b>Rs. {order.grand_total}</b>", bold_style)],
    ])

    summary_table = Table(summary_data, colWidths=[270, 150, 100])
    summary_table.setStyle(TableStyle([
        ('ALIGN', (1, 0), (-1, -1), 'RIGHT'),
        ('PADDING', (0, 0), (-1, -1), 4),
        ('LINEBELOW', (1, -1), (2, -1), 1, primary_color),
        ('LINEABOVE', (1, -1), (2, -1), 1, primary_color),
    ]))
    story.append(summary_table)
    story.append(Spacer(1, 20))

    # 5. Footer & Academic Disclaimer
    disclaimer_text = (
        "<b>Notice:</b> This document is generated for academic demonstration and evaluation of the "
        "SmartKart AI Major Project. No real financial transaction has taken place.<br/>"
        "Thank you for shopping with <b>SmartKart AI</b> — Fresh, Fast & Intelligent Grocery Delivery!"
    )
    disclaimer_p = Paragraph(disclaimer_text, subtitle_style)
    story.append(disclaimer_p)

    doc.build(story)
    pdf = buffer.getvalue()
    buffer.close()

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="SmartKart_Invoice_{order.order_number}.pdf"'
    response.write(pdf)
    return response
