# Backend Flask para Cloud Run

Este backend expone `/predict` para la demo de precios y endpoints OCR para facturas. Soporta dos modos:
- Modelo real: coloca `real_estate_model_pipeline_v2.pkl` junto a `app.py` o configura `MODEL_PATH`.
- Simulado: si no hay modelo, responde con una estimación determinística para pruebas.

## Endpoints OCR

- `POST /ocr/text`: devuelve `{ "text": "..." }`
- `POST /ocr/structured`: devuelve JSON con `{ empresa, ruc, fecha, total, articulos[] }`

Payload esperado:

```json
{
  "mimeType": "image/png",
  "filename": "factura.png",
  "base64": "..."
}
```

> Nota: por simplicidad, solo se aceptan imágenes (PNG/JPG/WEBP/TIFF).

## Ejecutar en local

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
# Opción 1: servidor desarrollo
python app.py  # http://localhost:8080
# Opción 2: producción local
export PORT=8080
gunicorn -b 0.0.0.0:$PORT app:app
```

Si ves "gunicorn: command not found", asegúrate de haber instalado `requirements.txt` o instala:

```bash
pip install gunicorn
```

## Variables de entorno

- `MODEL_PATH`: ruta del modelo para `/predict`
- `GEMINI_API_KEY`: API key de Gemini para `/ocr/structured`
- `GEMINI_MODEL`: modelo Gemini (por defecto `gemini-1.5-flash`)

Para Vision API, usa el Service Account del servicio de Cloud Run con permisos de Vision (recomendado).

## Despliegue en Google Cloud Run (recomendado)

Prerrequisitos:
- `gcloud` autenticado (`gcloud init`) y proyecto seleccionado.
- Habilitar APIs:

```bash
gcloud services enable run.googleapis.com cloudbuild.googleapis.com
```

### Opción A: Con Dockerfile

```bash
cd backend
PROJECT_ID=$(gcloud config get-value project)
REGION=us-central1
IMAGE=gcr.io/$PROJECT_ID/quai-pricing-api:latest

# Construir imagen
gcloud builds submit --tag $IMAGE .

# Desplegar en Cloud Run
gcloud run deploy quai-pricing-api \
  --image $IMAGE \
  --region $REGION \
  --platform managed \
  --allow-unauthenticated \
  --max-instances 1
```

Toma la URL que devuelve el comando (por ejemplo, `https://quai-pricing-api-xxxxx-uc.a.run.app`).

### Opción B: Buildpacks (sin Dockerfile)

```bash
cd backend
REGION=us-central1

gcloud run deploy quai-pricing-api \
  --source . \
  --use-dockerfile=false \
  --region $REGION \
  --allow-unauthenticated
```

> Cloud Run construirá la imagen a partir de `requirements.txt` y ejecutará `gunicorn` automáticamente si lo detecta. Si no, agrega un `Procfile` o usa la Opción A.

## CORS

Por defecto se permite cualquier origen en desarrollo. En producción, restringe orígenes en `Flask-CORS` o coloca un proxy en tu frontend.

## Conectar frontend (Vite)

En el proyecto React, configura `VITE_API_URL` con la URL de Cloud Run:

```bash
# en la raíz del frontend (propuesta-web/.env.local)
VITE_API_URL=https://quai-pricing-api-xxxxx-uc.a.run.app
```

Inicia el frontend y prueba el formulario de la demo.
