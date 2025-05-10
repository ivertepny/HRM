FROM python:3.10-alpine

# Environment variables for Python optimization
ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Set working directory
WORKDIR /usr/src

# Install system dependencies
RUN apt-get update && apt-get install --no-install-recommends -y \
    gcc \
    libpq-dev \
    graphviz \
    && rm -rf /var/lib/apt/lists/*

# Upgrade pip
RUN pip install --upgrade pip

# Copy requirements file and install Python dependencies
COPY ./requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Expose port 8000 for Django development server
EXPOSE 8000

# Copy application code
COPY . .

# Default entrypoint and command
ENTRYPOINT ["sh", "-c"]
CMD ["python manage.py makemigrations && python manage.py migrate && python manage.py runserver 0.0.0.0:8000"]
