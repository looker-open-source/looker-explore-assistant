# Use the official Python runtime as a parent image
FROM python:3.10-slim

# Set the working directory in the container
WORKDIR /app

# Copy the current directory contents into the container at /app
COPY requirements.txt .
COPY mcp_server.py .

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Make port 8080 available to the world outside this container
EXPOSE 8080

# Set environment variable for Flask to run on Cloud Run
ENV PORT=8080
ENV FLASK_ENV=production

# Run the application
CMD ["python", "mcp_server.py"]
