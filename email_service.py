import html
import logging
import os

import resend

logger = logging.getLogger(__name__)
LOGO_URL = 'https://res.cloudinary.com/cwj8d38f/image/upload/v1789729870/Boldstone_logo_hiv7pl.jpg'


def send_lease_application_confirmation(application):
    api_key = os.getenv('RESEND_API_KEY', '').strip()
    from_email = os.getenv('RESEND_FROM_EMAIL', '').strip()
    from_name = os.getenv('RESEND_FROM_NAME', 'Boldstone Investments Team').strip()

    if not api_key or not from_email:
        logger.warning('Resend is not configured; lease confirmation email was skipped.')
        return False

    resend.api_key = api_key
    name = html.escape(application.full_name)
    plan = html.escape(application.plan)
    country = html.escape(application.country)
    sender = f'{from_name} <{from_email}>'

    try:
        resend.Emails.send({
            'from': sender,
            'to': [application.email],
            'subject': f'Thank you, {application.full_name} - your lease application',
            'reply_to': from_email,
            'html': f'''
                <div style="font-family: Arial, sans-serif; color: #173b34; line-height: 1.6; max-width: 640px;">
                    <div style="padding: 8px 0 24px; text-align: center; border-bottom: 1px solid #dceae6;">
                        <img src="{LOGO_URL}" alt="Boldstone Investments" width="110" height="110" style="display: block; width: 110px; height: 110px; max-width: 100%; margin: 0 auto; border-radius: 50%; object-fit: cover;" />
                    </div>
                    <h2 style="color: #0f8972;">Thank you for your application, {name}</h2>
                    <p>Dear {name},</p>
                    <p>Thank you for your interest in leasing land with Boldstone Investments. We have received your application and appreciate the opportunity to learn more about your plans for coffee farming.</p>
                    <p><strong>Selected plan:</strong> {plan}<br><strong>Country:</strong> {country}</p>
                    <p>Our team will review the information provided and contact you shortly to discuss availability, the application process, and the next steps.</p>
                    <p>Kind regards,<br><strong>Boldstone Investments Team</strong><br>Coffee farming and agricultural investment in Uganda</p>
                </div>
            ''',
        })
        return True
    except Exception:
        logger.exception('Unable to send lease application confirmation email.')
        return False


def send_shop_order_confirmation(orders, invoice_number):
    if not orders:
        return False
    api_key = os.getenv('RESEND_API_KEY', '').strip()
    from_email = os.getenv('RESEND_FROM_EMAIL', '').strip()
    from_name = os.getenv('RESEND_FROM_NAME', 'Boldstone Investments Team').strip()
    if not api_key or not from_email:
        logger.warning('Resend is not configured; shop order confirmation email was skipped.')
        return False

    resend.api_key = api_key
    first = orders[0]
    name = html.escape(first.name)
    invoice = html.escape(invoice_number)
    address_lines = [
        first.country,
        first.province,
        f'{first.district} District' if first.district else None,
        ', '.join(part for part in (first.street, first.village) if part),
    ]
    address = '<br>'.join(html.escape(line) for line in address_lines if line)
    total_quantity = sum(order.quantity for order in orders)
    total = sum(order.quantity * order.product.price for order in orders)
    rows = ''.join(
        f'<tr><td style="padding:10px 8px;border-bottom:1px solid #dceae6;">{html.escape(order.product_name)}</td>'
        f'<td style="padding:10px 8px;border-bottom:1px solid #dceae6;text-align:center;">{order.quantity:,}</td>'
        f'<td style="padding:10px 8px;border-bottom:1px solid #dceae6;text-align:right;white-space:nowrap;">UGX {order.quantity * order.product.price:,.0f}</td></tr>'
        for order in orders
    )
    sender = f'{from_name} <{from_email}>'
    try:
        resend.Emails.send({
            'from': sender,
            'to': [first.email],
            'subject': f'Order confirmation {invoice_number} - Boldstone Investments',
            'reply_to': from_email,
            'html': f'''
                <div style="font-family:Arial,sans-serif;color:#173b34;line-height:1.6;max-width:680px;margin:0 auto;">
                    <div style="padding:8px 0 24px;text-align:center;border-bottom:1px solid #dceae6;">
                        <img src="{LOGO_URL}" alt="Boldstone Investments" width="110" height="110" style="display:block;width:110px;height:110px;max-width:100%;margin:0 auto;border-radius:50%;object-fit:cover;" />
                    </div>
                    <p style="margin-top:28px;">Dear {name},</p>
                    <p>Thank you for choosing <strong>Boldstone Investments</strong>.</p>
                    <p>We&rsquo;re pleased to confirm that we have received your order for coffee and tree seedlings. Our team will contact you shortly to confirm your order details and arrange delivery.</p>
                    <h2 style="margin:28px 0 12px;color:#0f8972;font-size:20px;">Order Details</h2>
                    <p><strong>Invoice Number:</strong> {invoice}</p>
                    <p><strong>Delivery Address:</strong><br>{address}</p>
                    <h2 style="margin:28px 0 12px;color:#0f8972;font-size:20px;">Items Ordered</h2>
                    <table style="width:100%;border-collapse:collapse;border:1px solid #dceae6;">
                        <thead><tr style="background:#edf7f4;"><th style="padding:10px 8px;text-align:left;">Item</th><th style="padding:10px 8px;text-align:center;">Quantity</th><th style="padding:10px 8px;text-align:right;">Amount</th></tr></thead>
                        <tbody>{rows}</tbody>
                        <tfoot><tr><td colspan="2" style="padding:12px 8px;text-align:right;"><strong>Total</strong></td><td style="padding:12px 8px;text-align:right;white-space:nowrap;"><strong>{total_quantity:,} items<br>UGX {total:,.0f}</strong></td></tr></tfoot>
                    </table>
                    <p><strong>Order Status:</strong> Received</p>
                    <p>Please keep your invoice number <strong>{invoice}</strong> for future reference when contacting our team about this order.</p>
                    <p>Thank you for trusting <strong>Boldstone Investments</strong> for your agricultural needs. We look forward to serving you.</p>
                    <p>Kind regards,<br><strong>Boldstone Investments Team</strong><br><em>Coffee Farming &amp; Agricultural Investment in Uganda</em></p>
                </div>
            ''',
        })
        return True
    except Exception:
        logger.exception('Unable to send shop order confirmation email.')
        return False
