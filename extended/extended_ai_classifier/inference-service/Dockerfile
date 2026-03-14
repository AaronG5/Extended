FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ ./app/

# saved_model/ is mounted at runtime via docker-compose volume,
# so it does NOT need to be baked into the image.

ENV MODEL_PATH=saved_model/model_250hz.json
ENV ENCODER_PATH=saved_model/label_encoder.pkl

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
