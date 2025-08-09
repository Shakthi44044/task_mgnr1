FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY task_manager ./task_manager

EXPOSE 5000

CMD ["gunicorn", "-b", "0.0.0.0:5000", "task_manager.run:app"]
