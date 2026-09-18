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