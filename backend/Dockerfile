# Start from the official Python 3.10 image
FROM python:3.10

# Set the working directory inside the container
WORKDIR /app

# Copy your requirements file first (for better caching)
COPY ./requirements.txt /app/requirements.txt

# Install dependencies using pip
RUN pip install --no-cache-dir --upgrade -r /app/requirements.txt

# Copy your 'app' directory into the container
COPY ./app /app/app

# Run the application
# We point to app/main.py because we are inside /app
CMD ["fastapi", "run", "app/main.py", "--port", "80"]