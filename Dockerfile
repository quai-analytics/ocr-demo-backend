# Imagen ligera con Python
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Instalar dependencias del sistema si hiciera falta (descomentarlas si scikit-learn lo requiere en tu región)
# RUN apt-get update && apt-get install -y --no-install-recommends \
#     build-essential \
#     && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copiar código
COPY . .

# Cloud Run escucha en 8080
EXPOSE 8080

# Iniciar con gunicorn (Flask WSGI)
CMD ["gunicorn", "-b", "0.0.0.0:8080", "app:app"]
