# Deployment en Google Cloud Run

Esta guía te ayuda a deployar el backend en Cloud Run.

## Prerrequisitos

- Cuenta de Google Cloud con proyecto activo
- `gcloud` CLI instalada
- Docker (opcional localmente)

## Pasos para deployar

### 1. Autenticarse en Google Cloud

```bash
gcloud auth login
gcloud config set project YOUR_PROJECT_ID
```

### 2. Configurar las variables de entorno en Cloud Run

Desde Google Cloud Console:

1. Ve a **Cloud Run**
2. Crea un nuevo servicio o edita el existente
3. En **Variables de entorno**, añade:

```
GEMINI_API_KEY=your-gemini-api-key
GEMINI_MODEL=gemini-1.5-flash
GOOGLE_SHEETS_ID=your-spreadsheet-id
GOOGLE_SHEETS_CREDENTIALS={"type":"service_account",...}
GOOGLE_SHEETS_WORKSHEET=Facturas
PORT=8080
```

**Importante:** Usa **Secretos de Google Cloud** para valores sensibles:
- GEMINI_API_KEY
- GOOGLE_SHEETS_CREDENTIALS

### 3. Deployar desde GitHub

Opción A: Desde la consola de Google Cloud:
1. Cloud Run → Crear servicio
2. Fuente: "GitHub"
3. Conecta tu repo
4. Rama: main
5. Tipo de compilación: "Dockerfile"
6. Configurar variables de entorno
7. Deployar

Opción B: Desde terminal:
```bash
gcloud run deploy ocr-backend \
  --source . \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars "GEMINI_API_KEY=YOUR_KEY,GOOGLE_SHEETS_ID=YOUR_ID"
```

### 4. Configurar Secretos (para datos sensibles)

```bash
# Crear secreto
echo -n "your-gemini-api-key" | gcloud secrets create gemini-api-key --data-file=-

# Usar en Cloud Run
gcloud run services update ocr-backend \
  --update-secrets GEMINI_API_KEY=gemini-api-key:latest \
  --region us-central1
```

### 5. Verificar el deployment

```bash
# Obtener URL
gcloud run services describe ocr-backend --region us-central1

# Probar el endpoint
curl https://ocr-backend-xxxxx.run.app/
```

## Variables de entorno requeridas

| Variable | Valor | Type |
|----------|-------|------|
| GEMINI_API_KEY | Tu API key de Gemini | Secret |
| GEMINI_MODEL | gemini-1.5-flash | Config |
| GOOGLE_SHEETS_ID | ID de tu spreadsheet | Config |
| GOOGLE_SHEETS_CREDENTIALS | JSON del service account | Secret |
| GOOGLE_SHEETS_WORKSHEET | Nombre de la hoja (opcional) | Config |
| PORT | 8080 | Config |

## Conectar desde el Frontend (Cloudflare)

En tu frontend, usa esta URL base:
```javascript
const API_URL = "https://ocr-backend-xxxxx.run.app";
```

## Monitoreo

Desde Google Cloud Console:
- Cloud Run → Logs: Ver logs en tiempo real
- Cloud Run → Métricas: CPU, memoria, requests

## Solución de problemas

### Build falla
```bash
# Ver logs de build
gcloud builds log $(gcloud builds list --limit=1 --format='value(id)')
```

### Servicio retorna 500
- Verifica las variables de entorno
- Revisa los logs en Cloud Logging
- Asegúrate de que GEMINI_API_KEY es válida

### Timeout en Google Sheets
- Verifica que GOOGLE_SHEETS_CREDENTIALS es válido
- Verifica que el service account tiene acceso a la hoja
- Aumenta el timeout en Cloud Run (Memory: 512MB, Timeout: 300s)

## Redeploy después de cambios

```bash
# Con GitHub integration, los cambios en main se despliegan automáticamente
# O manualmente:
gcloud run deploy ocr-backend --source . --region us-central1
```

## Variables para CORS (si necesitas)

El backend ya tiene CORS habilitado con Flask-CORS. Si necesitas restringir:

Edita `app.py` y cambia:
```python
CORS(app)  # Permitir cualquier origen
```

A:
```python
CORS(app, resources={r"/api/*": {"origins": ["https://tudominio.com"]}})
```

## Pricing

- Primeras 2 millones de requests: **gratis**
- $0.40 por millón de requests adicionales
- vCPU bajo demanda: ~$0.0000025 por segundo

Para una app pequeña, probablemente sea dentro del tier gratuito.
