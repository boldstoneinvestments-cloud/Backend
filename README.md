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

## Farmer portal

The farmer dashboard uses this same backend. Farmer accounts have separate sign-in and farmer-scoped API tokens, even though their credentials use Django's existing user store.

Farmer authentication endpoints are `POST /api/farmer/auth/sign-up`, `POST /api/farmer/auth/sign-in`, `POST /api/farmer/auth/sign-out`, and `GET`/`PATCH /api/farmer/auth/me`. Send the returned token as `Authorization: Bearer <token>` to access `GET /api/farmer/dashboard`, `/performance`, `/prices`, `/agronomy`, `/harvest`, `/opportunities`, `/rewards`, `/advice`, and `/loans`.

Farmers can add agronomy tasks and mark their tasks complete, submit or update harvest estimates, record coffee deliveries, and submit loan applications. All records are scoped to their own farm. Payment status and loan review status remain admin-controlled. Prices, yield/performance records, opportunities, reward balances and rules, advice banners/articles, and portal settings are managed in Django admin. Configure interest rate, weather guidance, and dashboard notices under Farmer portal settings. Add initial coffee prices and publish advice/opportunities before expecting those pages to show content.

Apply schema changes with `python manage.py migrate` before starting the backend.

## Railway

Create the Railway service from this repository with the service root directory set to the repository root (leave the root directory unset). `manage.py`, `requirements.txt`, and `railway.toml` are at the repository root. Railway will use `railway.toml` to run migrations and start Gunicorn. Set `DJANGO_SECRET_KEY`, `DJANGO_ALLOWED_HOSTS`, and `CORS_ALLOWED_ORIGINS` in the Railway service variables.

For shared caching across backend workers, add a Railway Redis service and set this service's `REDIS_URL` variable to the Redis service's private connection URL. Admin users, customers, orders, lease applications, chats, activity, product catalog, estate totals, and customer chat responses are cached and invalidated when their source data changes. Without Redis, the backend falls back to per-process memory caching.

For signed shop image uploads, set `CLOUDINARY_CLOUD_NAME`, `CLOUDINARY_API_KEY`, and `CLOUDINARY_API_SECRET` in the Railway **Backend** service variables. The API secret is only used by the backend to sign uploads and is never sent to the browser.

Set `ADMIN_USERNAME`, `ADMIN_EMAIL`, and `ADMIN_PASSWORD` in Railway variables. The deployment creates the admin account automatically, and you can view shop orders at `https://your-backend-domain/admin/shop/shoporder/`.

Admin sign-in requires a separate authenticator setup for each selected identity. After entering admin credentials, select Ssemata, Moses, or Habib and scan the displayed QR code with an authenticator app. Save the recovery codes shown after enrollment.

The next backend deployment runs one-time migrations to reset the authenticators and recovery codes for Ssemata, Moses, and Habib so they can enroll again. Later deployments will not repeat these resets.

For personalized lease application confirmations, set `RESEND_API_KEY`, `RESEND_FROM_EMAIL` (a verified Resend sender), and `RESEND_FROM_NAME=Boldstone Investments Team`. The applicant receives a formal confirmation email after the application is saved.

Shop orders collect structured delivery details and send the customer a Resend confirmation with an invoice number, item summary, quantities, address, and total.

### One-time database reset

For a full PostgreSQL reset without service-terminal access, add a Railway variable named `DATABASE_RESET_KEY` with a new random value and redeploy. This is an optional destructive operation; normal deployments only run migrations and preserve existing data.