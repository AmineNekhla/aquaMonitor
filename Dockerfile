# Use an official lightweight Python image
FROM python:3.11-slim

# Prevent Python from writing .pyc files or buffering stdout/stderr
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Set the working directory inside the container
WORKDIR /app

# Copy the requirements file into the container
# (psycopg2-binary is pre-compiled – no system build deps needed)
COPY requirements.txt /app/

# Upgrade pip and install Python dependencies
RUN pip install --upgrade pip && \
    pip install -r requirements.txt && \
    pip install django-celery-beat==2.5.0

# Copy the entire project code into the container
COPY . /app/

# Expose the standard Django port
EXPOSE 8000

# Start the Django development server (suitable for student projects)
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
