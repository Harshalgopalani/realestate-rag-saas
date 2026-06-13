# 1. Use an official, lightweight Python image
FROM python:3.10-slim

# 2. Set the working directory inside the container
WORKDIR /app

# 3. Copy the requirements file and install dependencies
COPY requirements.txt .
# We install sqlite3 and other system dependencies just in case
RUN apt-get update && apt-get install -y sqlite3 && rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir -r requirements.txt

# 4. Copy the rest of your backend code into the container
COPY . .

# 5. Expose the port FastAPI runs on
EXPOSE 8000

# 6. Start the server when the container boots
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]