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
    address = '<br>'.join(filter(None, [first.country, first.province, first.district, first.street, first.village]))
    address = html.escape(address).replace('&lt;br&gt;', '<br>')
    total = sum(order.quantity * order.product.price for order in orders)
    rows = ''.join(
        f'<tr><td style="padding:8px;border-bottom:1px solid #dceae6;">{html.escape(order.product_name)}</td>'
        f'<td style="padding:8px;border-bottom:1px solid #dceae6;text-align:center;">{order.quantity}</td>'
        f'<td style="padding:8px;border-bottom:1px solid #dceae6;text-align:right;">UGX {order.quantity * order.product.price:,.0f}</td></tr>'
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
                <div style="font-family:Arial,sans-serif;color:#173b34;line-height:1.6;max-width:680px;">
                    <div style="padding:8px 0 24px;text-align:center;border-bottom:1px solid #dceae6;">
                        <img src="{LOGO_URL}" alt="Boldstone Investments" width="110" height="110" style="display:block;width:110px;height:110px;max-width:100%;margin:0 auto;border-radius:50%;object-fit:cover;" />
                    </div>
                    <h2 style="color:#0f8972;">Thank you for your order, {name}</h2>
                    <p>Thank you for ordering coffee and farm products from Boldstone Investments. Your order has been received and our team will contact you to confirm delivery.</p>
                    <p><strong>Invoice number:</strong> {invoice_number}<br><strong>Delivery address:</strong><br>{address}</p>
                    <table style="width:100%;border-collapse:collapse;"><thead><tr><th style="text-align:left;padding:8px;">Item</th><th style="padding:8px;">Qty</th><th style="text-align:right;padding:8px;">Amount</th></tr></thead><tbody>{rows}</tbody><tfoot><tr><td colspan="2" style="padding:12px 8px;text-align:right;"><strong>Total</strong></td><td style="padding:12px 8px;text-align:right;"><strong>UGX {total:,.0f}</strong></td></tr></tfoot></table>
                    <p>Kind regards,<br><strong>Boldstone Investments Team</strong><br>Coffee farming and agricultural investment in Uganda</p>
                </div>
            ''',
        })
        return True
    except Exception:
        logger.exception('Unable to send shop order confirmation email.')
        return False
