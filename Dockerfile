FROM python:3.11-slim

WORKDIR /app

# System deps for google libs (if needed)
RUN apt-get update && apt-get install -y build-essential libffi-dev && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# copy app
COPY . .

# create data dirs
RUN mkdir -p data/sessions data/tokens data/downloads

ENV PYTHONUNBUFFERED=1

CMD ["python", "-m", "app"]
