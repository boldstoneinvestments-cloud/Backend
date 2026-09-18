# Boldstone Django backend

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python manage.py makemigrations api
python manage.py migrate
python manage.py runserver 5000
```

API endpoints: `GET /api/health`, `GET /api/estate`, `POST /api/estate/invest`, `POST /api/orders`, and `POST /api/contact`.

## Railway

Create a Railway service from this repository with the service root directory set to `backend`. Railway will use `railway.toml` to run migrations and start Gunicorn. Set `DJANGO_SECRET_KEY`, `DJANGO_ALLOWED_HOSTS`, and `CORS_ALLOWED_ORIGINS` in the Railway service variables.

Set `ADMIN_USERNAME`, `ADMIN_EMAIL`, and `ADMIN_PASSWORD` in Railway variables. The deployment creates the admin account automatically, and you can view shop orders at `https://your-backend-domain/admin/shop/shoporder/`.

For personalized lease application confirmations, set `RESEND_API_KEY`, `RESEND_FROM_EMAIL` (a verified Resend sender), and `RESEND_FROM_NAME=Boldstone Investments Team`. The applicant receives a formal confirmation email after the application is saved.

Shop orders collect structured delivery details and send the customer a Resend confirmation with an invoice number, item summary, quantities, address, and total.

### One-time database reset

For a full PostgreSQL reset without service-terminal access, add a Railway variable named `DATABASE_RESET_KEY` with a new random value and redeploy. This is an optional destructive operation; normal deployments only run migrations and preserve existing data.