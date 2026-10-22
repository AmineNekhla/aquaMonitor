# aquaMonitor

A Django web app for monitoring fish farm ponds. I built this to explore IoT-style monitoring — the idea is that sensors and cameras on each pond feed data into the system, and the app tracks water quality, generates alerts, and gives farm managers a live view of what's going on.

## Features

- Dashboard with pond health stats and active alerts
- Farms and ponds management (add/view/edit)
- Sensor readings per pond with trend visualization
- Camera feeds and AI-based detection logs
- Alert center to review and acknowledge warnings
- User profiles with role-based access

## Running with Docker (easiest way)

`ash
docker compose up --build
`

Then in a second terminal:

`ash
docker compose exec web python manage.py migrate
docker compose exec web python manage.py createsuperuser
`

To populate with sample data (30 days of realistic readings, simulated stress events, etc.):

`ash
docker compose exec web python manage.py seed_db --clear
`

App will be at http://localhost:8000/ and admin at http://localhost:8000/admin/.

## Manual setup (no Docker)

`ash
python -m venv venv
source venv/bin/activate  # or venv\Scripts\Activate.ps1 on Windows
pip install -r requirements.txt
copy .env.example .env  # then set DB_HOST=localhost
`

Create the database in psql:
`sql
CREATE DATABASE aquaculture_db;
`

Then:
`ash
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
`

## Project structure

`
aquaMonitor/
├── aquaculture/        # Django settings
├── monitoring/         # Main app (models, views, urls, forms, templates)
├── static/css/
├── Dockerfile
├── docker-compose.yml
└── requirements.txt
`

## Stack

Python 3.11, Django, PostgreSQL, Docker