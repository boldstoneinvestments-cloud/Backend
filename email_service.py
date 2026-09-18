import html
import logging
import os

import resend

logger = logging.getLogger(__name__)


def send_lease_application_confirmation(application):
    api_key = os.getenv('RESEND_API_KEY', '').strip()
    from_email = os.getenv('RESEND_FROM_EMAIL', '').strip()
    from_name = os.getenv('RESEND_FROM_NAME', 'Boldstone Investments').strip()

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
            'subject': f'Thank you, {application.full_name} - Boldstone lease application received',
            'reply_to': from_email,
            'html': f'''
                <div style="font-family: Arial, sans-serif; color: #173b34; line-height: 1.6; max-width: 640px;">
                    <h2 style="color: #0f8972;">Thank you for your application, {name}</h2>
                    <p>Dear {name},</p>
                    <p>Thank you for your interest in leasing land with Boldstone Investments. We have received your application and appreciate the opportunity to learn more about your plans for coffee farming.</p>
                    <p><strong>Selected plan:</strong> {plan}<br><strong>Country:</strong> {country}</p>
                    <p>Our team will review the information provided and contact you shortly to discuss availability, the application process, and the next steps.</p>
                    <p>Kind regards,<br><strong>Boldstone Investments</strong><br>Coffee farming and agricultural investment in Uganda</p>
                </div>
            ''',
        })
        return True
    except Exception:
        logger.exception('Unable to send lease application confirmation email.')
        return False
