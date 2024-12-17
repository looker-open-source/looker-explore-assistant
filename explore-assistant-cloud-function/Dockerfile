# Use the official Python image as a base image
FROM python:3.11.11-slim

# for local dev 
ENV GOOGLE_APPLICATION_CREDENTIALS="/app/service_account.json"

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc libpq-dev && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# Copy the app's files into the container
WORKDIR /app
COPY main.py /app
COPY test.py /app
COPY requirements.txt /app

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Set the entrypoint to run the Flask app
CMD ["python", "main.py"]
