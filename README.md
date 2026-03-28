# 🐟 Smart Aquaculture Monitoring System

A Django web application for monitoring fish farm ponds using sensors, cameras, and AI-based detections.

---

## 🚀 Quick Start (Docker - Recommended)

To run the application instantly **without installing Python or PostgreSQL**, you can use Docker.

### 1. Build and Run the Project
Open a terminal in the `aquaMonitor` directory and run:
```bash
docker compose up --build
```
*Wait until you see logs indicating the database is ready and the development server is running. Leave this terminal open.*

### 2. Setup the Database (First-Time Only)
Open a **new, separate terminal** in the same folder and run migrations and create your admin account:
```bash
docker compose exec web python manage.py migrate
docker compose exec web python manage.py createsuperuser
```
*(Enter a username, email, and password when prompted).*

### 3. Seed the Database (Populate with Realistic Data)
Instead of manually adding every farm, pond, and sensor, use the custom seeding script. This generates 30 days of realistic, time-staggered sensor data, including oxygen crashes and automated AI alerts.

```bash
docker compose exec web python manage.py seed_db --clear
```
What this does:

- Creates an admin and 3 farm managers.
- Sets up 3 unique farms with 9 total ponds (including High-Risk and Healthy zones).
- Generates sensor readings with realistic daily cycles.
- Simulates "Stress Events".
- Runs an initial AI inference to generate health forecasts.

### 4. Access the Application
- Web Dashboard: **http://localhost:8000/**
- Admin Panel: **http://localhost:8000/admin/**

---

## ⚙️ Manual Setup (Optional)

**⚠️ Note: Follow these steps ONLY if you are not using Docker.**

### 1. Environment Setup
```bash
python -m venv venv
# Windows:
venv\Scripts\Activate.ps1
# Mac/Linux:
source venv/bin/activate

pip install -r requirements.txt
```

### 2. Configure the Database
Copy the example env file:
```bash
copy .env.example .env
```
Edit `.env` and set `DB_HOST=localhost`. Then create the PostgreSQL database (run in psql or pgAdmin):
```sql
CREATE DATABASE aquaculture_db;
```

### 3. Run migrations and start server
```bash
python manage.py makemigrations
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

---

## 📁 Project Structure

```
aquaMonitor/
│
├── aquaculture/                  # Django project configuration
├── monitoring/                   # Main application
│   ├── models.py                 # Database models
│   ├── views.py                  # All views (dashboard, farms, ponds, alerts)
│   ├── urls.py                   # App-level routing
│   ├── forms.py                  # Django forms
│   └── templates/monitoring/     # HTML templates
│
├── static/css/                   # Custom CSS styles
├── manage.py                     # Django CLI
├── requirements.txt              # Python dependencies
├── .env.example                  # Environment variable template
│
├── Dockerfile                    # Docker image build instructions
├── docker-compose.yml            # Multi-container orchestration
└── .dockerignore                 # Excluded build files
```

---

## 📊 Pages / Features

| URL | Page | Description |
|---|---|---|
| `/` | Dashboard | Executive KPI overview (Fish stock, Alerts, Water Quality) |
| `/farms/` | Farms List | View all registered farms or add new ones |
| `/farms/<id>/` | Farm Detail | Farm info and list of associated ponds |
| `/ponds/` | Ponds Overview | Sparkline trends and latest readings across all ponds |
| `/ponds/<id>/` | Pond Detail | Deep dive into live sensor readings, cameras, AI logs |
| `/alerts/` | Alerts Center | Review and acknowledge system safety warnings |
| `/profile/` | User Profile | Update your user and role definitions |

---

## 🧠 Models Overview

| Model | Description |
|---|---|
| `Profile` | Extends User with phone and role |
| `Farm` | Fish farm owned by a user |
| `Pond` | Pond inside a farm |
| `Sensor` | Monitoring sensor on a pond |
| `SensorReading` | One measurement from a sensor |
| `Camera` | IP camera on a pond |
| `AIDetection` | AI analysis result from a camera |
| `Alert` | Warning/critical event for a pond |

---

## 🐳 Docker Details (Advanced)

If you are using Docker, here is how the orchestration works behind the scenes:

- **Services**: `docker-compose.yml` runs two container services: `web` (Django + Python 3.11) and `db` (PostgreSQL 15 Alpine).
- **Environment Automation (`.env`)**: The containers securely inject environment variables directly from inside your `.env` file. Docker automatically intercepts `POSTGRES_DB`, `POSTGRES_USER`, and `POSTGRES_PASSWORD` to initialize the database natively without hardcoding secrets.
- **Volumes**: Your code is mapped via a local volume so Python file changes update instantly (`StatReloader`). Database rows are saved in a durable Docker volume (`postgres_data`) so no information is lost when removing containers.
