FROM python:3.14-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY extended/ .

EXPOSE 8000

CMD ["gunicorn", "extended_api.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3"]