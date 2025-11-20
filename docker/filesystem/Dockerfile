
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY server.py .

# Create mount point
RUN mkdir /data
ENV PYTHONUNBUFFERED=1

ENTRYPOINT ["python", "server.py"]
