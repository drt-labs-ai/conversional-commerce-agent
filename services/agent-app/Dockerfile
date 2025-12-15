FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Chainlit default port
EXPOSE 8000

CMD ["chainlit", "run", "app.py", "-h"]
