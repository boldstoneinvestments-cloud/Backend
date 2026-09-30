# Boldstone Django backend

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python manage.py makemigrations api
python manage.py migrate
python manage.py runserver 5000
```

API endpoints: `GET /api/health`, `GET /api/estate`, `POST /api/estate/invest`, `POST /api/orders`, and `POST /api/contact`.

## Railway

Create the Railway service from this repository with the service root directory set to the repository root (leave the root directory unset). `manage.py`, `requirements.txt`, and `railway.toml` are at the repository root. Railway will use `railway.toml` to run migrations and start Gunicorn. Set `DJANGO_SECRET_KEY`, `DJANGO_ALLOWED_HOSTS`, and `CORS_ALLOWED_ORIGINS` in the Railway service variables.

Set the matching reCAPTCHA secret as `RECAPTCHA_SECRET_KEY` in this backend service. The public site key belongs in the frontend build environment; do not put it in this backend-only setting or expose the secret in frontend variables.

Set `ADMIN_USERNAME`, `ADMIN_EMAIL`, and `ADMIN_PASSWORD` in Railway variables. The deployment creates the admin account automatically, and you can view shop orders at `https://your-backend-domain/admin/shop/shoporder/`.

Admin sign-in requires a separate authenticator setup for each selected identity. After entering admin credentials, select Ssemata, Moses, or Habib and scan the displayed QR code with an authenticator app. Save the recovery codes shown after enrollment.

The next backend deployment runs a one-time migration to reset Ssemata's authenticator and recovery codes so she can enroll again. Later deployments will not repeat this reset.

For personalized lease application confirmations, set `RESEND_API_KEY`, `RESEND_FROM_EMAIL` (a verified Resend sender), and `RESEND_FROM_NAME=Boldstone Investments Team`. The applicant receives a formal confirmation email after the application is saved.

Shop orders collect structured delivery details and send the customer a Resend confirmation with an invoice number, item summary, quantities, address, and total.

### One-time database reset

For a full PostgreSQL reset without service-terminal access, add a Railway variable named `DATABASE_RESET_KEY` with a new random value and redeploy. This is an optional destructive operation; normal deployments only run migrations and preserve existing data.