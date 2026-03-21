# 🐟 Smart Aquaculture Monitoring System

A Django web application for monitoring fish farm ponds using sensors, cameras, and AI-based detections.

---

## Project Structure

```
aquaMonitor/
│
├── aquaculture/                  # Django project configuration
│   ├── settings.py               # App settings (env-based DB config)
│   ├── urls.py                   # Root URL routing
│   ├── wsgi.py                   # WSGI entry point
│   └── asgi.py                   # ASGI entry point
│
├── monitoring/                   # Main application
│   ├── models.py                 # Database models (Farm, Pond, Alert…)
│   ├── views.py                  # All views (dashboard, farms, ponds, alerts)
│   ├── urls.py                   # App-level URL patterns
│   ├── admin.py                  # Admin panel configuration
│   ├── forms.py                  # Django forms
│   ├── context_processors.py     # Global template context (notifications)
│   ├── migrations/               # Database migration files
│   └── templates/monitoring/     # HTML templates
│       ├── base.html             # Base layout (sidebar + topbar)
│       ├── login.html            # Login page
│       ├── dashboard.html        # Main dashboard
│       ├── farms.html            # Farms list
│       ├── farm_detail.html      # Single farm view
│       ├── ponds.html            # Ponds list
│       ├── pond_detail.html      # Single pond + sensor data
│       ├── alerts.html           # Alerts list
│       └── profile.html          # User profile
│
├── static/css/
│   └── main.css                  # Custom CSS styles
│
├── manage.py                     # Django CLI entry point
├── requirements.txt              # Python dependencies
├── .env.example                  # Environment variable template (safe to commit)
│
├── Dockerfile                    # Docker image build instructions
├── docker-compose.yml            # Multi-container setup (web + db)
└── .dockerignore                 # Files excluded from Docker build
```

The project follows standard Django app structure with a single `monitoring` app handling all business logic. Docker is used for containerized deployment with a PostgreSQL database. Environment variables are managed via `.env` (not committed) using `.env.example` as a safe template.

---

## Setup & Run Instructions

### 1. Navigate into the project folder
```bash
cd aquaP
```

### 2. Create a virtual environment
```bash
python -m venv venv
```

### 3. Activate the virtual environment
**Windows (PowerShell):**
```bash
venv\Scripts\Activate.ps1
```
**Mac/Linux:**
```bash
source venv/bin/activate
```

### 4. Install dependencies
```bash
pip install -r requirements.txt
```

### 5. Configure the database
Copy the example env file and fill in your PostgreSQL credentials:
```bash
copy .env.example .env
```
Edit `.env`:
```
SECRET_KEY=any-random-secret-key
DB_NAME=aquaculture_db
DB_USER=aqua_user
DB_PASSWORD=aqua_password
DB_HOST=localhost
DB_PORT=5432
DEBUG=True
```

Create the PostgreSQL database (run in psql or pgAdmin):
```sql
CREATE DATABASE aquaculture_db;
```

### 6. Run database migrations
```bash
python manage.py makemigrations
python manage.py migrate
```

### 7. Create a superuser (admin account)
```bash
python manage.py createsuperuser
```
Enter a username, email, and password when prompted.

### 8. Start the development server
```bash
python manage.py runserver
```

Open your browser at: **http://127.0.0.1:8000/**

---

## Pages

| URL | Page |
|---|---|
| `/` | Dashboard |
| `/farms/` | All Farms |
| `/farms/<id>/` | Farm Detail + Ponds |
| `/ponds/` | All Ponds |
| `/ponds/<id>/` | Pond Detail (sensors, cameras, detections, alerts) |
| `/alerts/` | All Alerts |
| `/profile/` | User Profile |
| `/admin/` | Django Admin Panel |
| `/login/` | Login Page |

---

## Adding Sample Data

The fastest way to add data for testing is through the Django admin:

1. Visit `http://127.0.0.1:8000/admin/`
2. Log in with your superuser account
3. Add Farms, Ponds, Sensors, Readings, Cameras, Detections, and Alerts

---

## Tech Stack

- **Backend**: Django 4.2, Python 3.11
- **Database**: PostgreSQL 15 (via psycopg2-binary)
- **Frontend**: Django Templates, Bootstrap 5, Bootstrap Icons
- **Auth**: Django built-in authentication + Profile model
- **Containerisation**: Docker + Docker Compose

---

## Models Overview

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

## 🐳 Docker Setup (Recommended)

To run the application instantly without installing Python, PostgreSQL, or setting up a virtual environment on your computer, you can use Docker.

### Prerequisites
- [Docker Desktop](https://www.docker.com/products/docker-desktop/) installed and running.

### 1. Build and Run the Project
Open a terminal in the `aquaP` directory and run:
```bash
docker compose up --build
```
This automatically downloads PostgreSQL, installs Django, configures the database, and starts the server. 

Wait until you see logs indicating the database is ready and the development server is running. Leave this terminal open.

### 2. Setup the Database (First-Time Only)
Open a **new, separate terminal** inside the same `aquaP` folder to execute the Django setup commands inside your running container:

**Run Migrations:**
```bash
docker compose exec web python manage.py makemigrations
docker compose exec web python manage.py migrate
```

**Create an Admin Account:**
```bash
docker compose exec web python manage.py createsuperuser
```
(Enter a username, email, and password when prompted).

### 3. Access the Application
Open your web browser and navigate to:
**http://localhost:8000/**

You can access your admin panel at:
**http://localhost:8000/admin/**

### 4. Stopping the Project
To safely shut down the server and database, use:
```bash
docker compose down
```

### 5. Resetting the Database
If you ever want to completely wipe the database clean and start over from scratch, run:
```bash
docker compose down -v
```
*(This destroys the `postgres_data` volume containing your tables/users).* Then simply run `docker compose up --build` again.
