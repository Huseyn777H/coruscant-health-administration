# Coruscant Health Administration

This is a Django project for the Qwasar Coruscant Health Administration task.

It includes:

- patient and doctor self-registration with administrator approval
- health reading uploads from patient devices
- doctor reports and service orders
- department result uploads
- emergency intake workflow
- encrypted document storage inside the database

## Stack

- Python 3.13
- Django 5
- SQLite for local use
- PostgreSQL or another database through `DATABASE_URL` for deployment

## Local run

```bash
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

## Deployment

Files added for deployment:

- `render.yaml` for Render deployment
- `Procfile`
- `.github/workflows/django.yml`

Basic steps:

1. Push the project to GitHub.
2. Create a new web service on Render.
3. Add the environment variables from `.env.example`.
4. Run migrations.
5. Put the final deployed URL into `my_coruscant_health_administration_url.txt`.
