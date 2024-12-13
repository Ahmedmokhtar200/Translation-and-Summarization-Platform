# Use a Python base image
FROM python:3.9-slim

# Set working directory
WORKDIR /app

# Copy requirements file and install dependencies
COPY requirements.txt /app

RUN pip install --no-cache-dir -r requirements.txt

# Copy the app code
COPY . /app

# Expose port
EXPOSE 8003

# Command to run the Flask app
CMD ["python", "app.py"]
