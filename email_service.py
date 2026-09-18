import html
import logging
import os

import resend

logger = logging.getLogger(__name__)
LOGO_URL = 'https://res.cloudinary.com/cwj8d38f/image/upload/v1789729870/Boldstone_logo_hiv7pl.jpg'
ADMIN_ORDER_EMAIL = os.getenv('RESEND_ADMIN_EMAIL', 'boldstone.investments@gmail.com').strip()


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
    address = html.escape(application.address or '')
    phone = html.escape(application.phone or '')
    plan_details = {
        'Starter Plan': {
            'price': 'US$49.99/month for the 1st year; renews at US$19.99/month',
            'description': 'Ideal for individuals, young professionals, and first-time coffee farmers who want to start with a manageable monthly commitment. You do not have to be Ugandan to subscribe.',
            'included': [
                'Annual lease of 1 acre of coffee farmland',
                'Land preparation and site establishment',
                'High-quality coffee seedlings',
                'Indigenous shade tree seedlings',
                'Planting and field layout',
                'Farm maintenance during establishment',
                'Agronomy supervision and technical support',
                'Progress updates and farm records',
                'Harvest preparation support',
            ],
        },
        'Growth Plan': {
            'price': 'US$569.99/year for the 1st year; renews at US$219.99/year',
            'description': 'Ideal for individuals, businesses, people in the diaspora, and clients with available capital who want their coffee farm established without waiting for a phased setup period.',
            'included': [
                'Annual lease of 1 acre of coffee farmland',
                'Land preparation and farm establishment',
                'High-quality coffee seedlings',
                'Planting and field layout',
                'Ongoing farm maintenance',
                'Agronomy supervision and technical support',
                'Periodic farm reports and production updates',
                'Harvest planning and coordination support',
            ],
        },
    }.get(application.plan, {'price': '', 'description': '', 'included': []})
    plan_price = html.escape(plan_details['price'])
    plan_description = html.escape(plan_details['description'])
    plan_included = ''.join(f'<li>{html.escape(item)}</li>' for item in plan_details['included'])
    sender = f'{from_name} <{from_email}>'
    try:
        resend.Emails.send({
            'from': sender,
            'to': [application.email],
            'subject': f'Thank you, {application.full_name} - your land lease request',
            'reply_to': from_email,
            'html': f'''
                <div style="font-family: Arial, sans-serif; color: #173b34; line-height: 1.6; max-width: 640px;">
                    <div style="padding: 8px 0 24px; text-align: center; border-bottom: 1px solid #dceae6;">
                        <img src="{LOGO_URL}" alt="Boldstone Investments" width="110" height="110" style="display: block; width: 110px; height: 110px; max-width: 100%; margin: 0 auto; border-radius: 50%; object-fit: cover;" />
                    </div>
                    <h2 style="color: #0f8972;">Thank you for your interest in leasing land, {name}</h2>
                    <p>Dear {name},</p>
                    <p>Thank you for choosing Boldstone Investments. We have received your request to join our coffee farming plan and appreciate your interest in developing a coffee farm.</p>
                    <p><strong>Selected coffee farming plan:</strong> {plan}<br><strong>Plan pricing:</strong> {plan_price}<br><strong>Country:</strong> {country}</p>
                    <p>{plan_description}</p>
                    <p><strong>What&rsquo;s included:</strong></p>
                    <ul>{plan_included}</ul>
                    <p>Our team will contact you shortly to confirm the payment details, provide more information about the lease, and guide you through the next steps.</p>
                    <p>We look forward to helping you begin your coffee farming journey with Boldstone Investments.</p>
                    <p>Kind regards,<br><strong>Boldstone Investments</strong><br>Coffee farming and agricultural investment in Uganda</p>
                </div>
            ''',
        })
        resend.Emails.send({
            'from': sender,
            'to': [ADMIN_ORDER_EMAIL],
            'subject': f'New lease request from {application.full_name} - Boldstone Investments',
            'reply_to': from_email,
            'html': f'''
                <div style="font-family:Arial,sans-serif;color:#173b34;line-height:1.6;max-width:640px;margin:0 auto;">
                    <div style="padding:8px 0 24px;text-align:center;border-bottom:1px solid #dceae6;">
                        <img src="{LOGO_URL}" alt="Boldstone Investments" width="110" height="110" style="display:block;width:110px;height:110px;max-width:100%;margin:0 auto;border-radius:50%;object-fit:cover;" />
                    </div>
                    <p style="margin-top:28px;">Hello Boldstone Investments Team,</p>
                    <p>A new lease request has been submitted through the <strong>Boldstone Investments</strong> website.</p>
                    <h2 style="margin:28px 0 12px;color:#0f8972;font-size:20px;">Lease Request</h2>
                    <p><strong>Customer:</strong> {name}<br><strong>Plan:</strong> {plan}<br><strong>Plan pricing:</strong> {plan_price}<br><strong>Status:</strong> Submitted<br><strong>Country:</strong> {country}<br><strong>Phone:</strong> {phone}<br><strong>Email:</strong> {html.escape(application.email)}</p>
                    <p><strong>Plan description:</strong> {plan_description}</p>
                    <p><strong>What&rsquo;s included:</strong></p>
                    <ul>{plan_included}</ul>
                    <p><strong>Address:</strong> {address or 'Not provided'}<br><strong>Notes:</strong> {html.escape(application.notes or 'None')}</p>
                    <p>Please contact the customer to confirm payment details and provide more information about the land lease.</p>
                    <p>Kind regards,<br><strong>Boldstone Investments System</strong><br><em>Automated Lease Notification</em><br><strong>Coffee Farming &amp; Agricultural Investment in Uganda</strong></p>
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
        logger.error('Order email skipped: RESEND_API_KEY and RESEND_FROM_EMAIL must be configured.')
        return False

    resend.api_key = api_key
    first = orders[0]
    name = html.escape(first.name)
    invoice = html.escape(invoice_number)
    country = html.escape(first.country or '')
    region = html.escape(first.province or '')
    district = html.escape(first.district or '')
    street = html.escape(first.street or '')
    village = html.escape(first.village or '')
    customer_address = '<br>'.join(
        line for line in (country, region, f'{district} District' if district else '', ', '.join(part for part in (street, village) if part)) if line
    )
    total_quantity = sum(order.quantity for order in orders)
    total = sum(order.quantity * order.product.price for order in orders)
    rows = ''.join(
        f'<tr><td style="padding:10px 8px;border-bottom:1px solid #dceae6;">{html.escape(order.product_name)}</td>'
        f'<td style="padding:10px 8px;border-bottom:1px solid #dceae6;text-align:center;">{order.quantity:,}</td>'
        f'<td style="padding:10px 8px;border-bottom:1px solid #dceae6;text-align:right;white-space:nowrap;">UGX {order.quantity * order.product.price:,.0f}</td></tr>'
        for order in orders
    )
    sender = f'{from_name} <{from_email}>'
    order_date = first.created_at.strftime('%d %B %Y')
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
                    <p><strong>Delivery Address:</strong><br>{customer_address}</p>
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
        resend.Emails.send({
            'from': sender,
            'to': [ADMIN_ORDER_EMAIL],
            'subject': f'New order {invoice_number} - Boldstone Investments',
            'reply_to': from_email,
            'html': f'''
                <div style="font-family:Arial,sans-serif;color:#173b34;line-height:1.6;max-width:680px;margin:0 auto;">
                    <div style="padding:8px 0 24px;text-align:center;border-bottom:1px solid #dceae6;">
                        <img src="{LOGO_URL}" alt="Boldstone Investments" width="110" height="110" style="display:block;width:110px;height:110px;max-width:100%;margin:0 auto;border-radius:50%;object-fit:cover;" />
                    </div>
                    <p style="margin-top:28px;">Hello Boldstone Investments Team,</p>
                    <p>A new order has been placed through the <strong>Boldstone Investments</strong> website and requires your attention.</p>
                    <h2 style="margin:28px 0 12px;color:#0f8972;font-size:20px;">New Order</h2>
                    <p><strong>Invoice Number:</strong> {invoice}<br><strong>Customer:</strong> {name}<br><strong>Order Status:</strong> Placed<br><strong>Order Date:</strong> {html.escape(order_date)}</p>
                    <h2 style="margin:28px 0 12px;color:#0f8972;font-size:20px;">Customer&rsquo;s Order</h2>
                    <table style="width:100%;border-collapse:collapse;border:1px solid #dceae6;">
                        <thead><tr style="background:#edf7f4;"><th style="padding:10px 8px;text-align:left;">Item</th><th style="padding:10px 8px;text-align:center;">Quantity</th><th style="padding:10px 8px;text-align:right;">Amount</th></tr></thead>
                        <tbody>{rows}</tbody>
                        <tfoot><tr><td colspan="2" style="padding:12px 8px;text-align:right;"><strong>Order Total</strong></td><td style="padding:12px 8px;text-align:right;white-space:nowrap;"><strong>{total_quantity:,} items<br>UGX {total:,.0f}</strong></td></tr></tfoot>
                    </table>
                    <h2 style="margin:28px 0 12px;color:#0f8972;font-size:20px;">Delivery Address</h2>
                    <p><strong>Country:</strong> {country}<br><strong>Region:</strong> {region}<br><strong>District:</strong> {district}<br><strong>Street:</strong> {street}<br><strong>Village:</strong> {village}</p>
                    <p>Please use <strong>{invoice}</strong> as the reference for this order.</p>
                    <p>Kind regards,<br><strong>Boldstone Investments System</strong><br><em>Automated Order Notification</em><br><strong>Coffee Farming &amp; Agricultural Investment in Uganda</strong></p>
                </div>
            ''',
        })
        return True
    except Exception:
        logger.exception('Unable to send shop order confirmation email.')
        return False
