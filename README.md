# Coruscant Health Administration

Coruscant Health Administration is a Django-based medical management system built for the Qwasar task requirements. It supports:

- patient and doctor self-registration with administrator approval
- health reading uploads from patient devices
- doctor reports and service orders
- department result uploads
- emergency intake workflow
- encrypted document storage inside the database

## Stack

- Python 3.13
- Django 5
- SQLite locally, cloud-ready via `DATABASE_URL`
- WhiteNoise + Gunicorn for deployment

## Local run

```bash
pip install -r requirements.txt
python manage.py migrate
python manage.py seed_demo
python manage.py runserver
```

Demo logins after `seed_demo`:

- `cha_admin` / `AdminPass123!`
- `patient_demo` / `PatientPass123!`
- `doctor_demo` / `DoctorPass123!`
- `department_demo` / `DepartmentPass123!`
- `emergency_demo` / `EmergencyPass123!`

## Deployment

The repository includes:

- `render.yaml` for Render deployment
- `Procfile` for process definition
- `.github/workflows/django.yml` for CI
- `/health/` for health checks
- `seed_demo` management command for reviewer-friendly sample data

## Submission-ready Render flow

1. Push this project to GitHub.
2. In Render, create the Blueprint from `render.yaml`.
3. After the first deploy finishes, open a Render shell and run `python manage.py seed_demo`.
4. Copy the live public URL and replace the content of `my_coruscant_health_administration_url.txt` with only that URL.

I used Render's current Blueprint fields such as `runtime`, `buildCommand`, `startCommand`, `healthCheckPath`, and generated env vars based on the official docs:

- [Blueprint YAML Reference](https://render.com/docs/blueprint-spec)
- [Deploy a Django App on Render](https://render.com/docs/deploy-django)
