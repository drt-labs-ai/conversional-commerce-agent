FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN apt-get update && apt-get install -y docker.io && rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Chainlit default port
EXPOSE 8000

CMD ["chainlit", "run", "app.py", "--host", "0.0.0.0", "--port", "8000", "-h"]
