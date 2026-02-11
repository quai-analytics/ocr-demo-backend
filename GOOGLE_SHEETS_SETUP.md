# Configuración de Google Sheets

Tu aplicación ahora envía automáticamente los datos de facturas a Google Sheets. Elige una de estas dos opciones:

## 1. Crear una hoja de cálculo en Google Sheets

1. Ve a [Google Sheets](https://sheets.google.com)
2. Crea una nueva hoja de cálculo
3. Copia el ID de la URL:
   ```
   https://docs.google.com/spreadsheets/d/[ESTE_ES_EL_ID]/edit
   ```

---

## OPCIÓN A: Service Account (Recomendado para producción)

### 2A. Crear credenciales de Google (Service Account)

1. Ve a [Google Cloud Console](https://console.cloud.google.com/)
2. Crea un nuevo proyecto (o usa uno existente)
3. Activa la API de Google Sheets:
   - Busca "Google Sheets API" y actívala
4. Crea credenciales de tipo "Service Account":
   - Ve a "Credenciales"
   - Haz clic en "Crear credenciales" → "Cuenta de servicio"
   - Completa los datos básicos
   - En "Acceso", selecciona "Editor"
5. Una vez creada, ve a la pestaña "Claves"
6. Crea una nueva clave JSON y descárgala

### 3A. Compartir la hoja con el Service Account

1. Abre el JSON descargado y copia el valor de `client_email`
2. Abre tu Google Sheet
3. Haz clic en "Compartir"
4. Pega el email del service account y dale permisos de "Editor"

### 4A. Configurar variables de entorno

```bash
export GOOGLE_SHEETS_ID="YOUR_SPREADSHEET_ID"
export GOOGLE_SHEETS_CREDENTIALS='{"type":"service_account","project_id":"...","private_key":"...","client_email":"..."}'
export GOOGLE_SHEETS_WORKSHEET="Facturas"  # Opcional, por defecto es "Facturas"
```

---

## OPCIÓN B: OAuth2 con Client ID + Secret (Para desarrollo)

### 2B. Crear credenciales OAuth2

1. Ve a [Google Cloud Console](https://console.cloud.google.com/)
2. Crea un nuevo proyecto (o usa uno existente)
3. Activa la API de Google Sheets:
   - Busca "Google Sheets API" y actívala
4. Crea credenciales de tipo "OAuth 2.0 - Aplicación de escritorio":
   - Ve a "Credenciales"
   - Haz clic en "Crear credenciales" → "ID de cliente OAuth"
   - Tipo: "Aplicación de escritorio"
   - Guarda y descarga el JSON
5. Extrae el `client_id` y `client_secret`

### 3B. Generar el Refresh Token

Ejecuta el script que genera el refresh token:

```bash
pip install -r requirements.txt

python get_google_token.py \
  --client-id "YOUR_CLIENT_ID.apps.googleusercontent.com" \
  --client-secret "YOUR_CLIENT_SECRET"
```

Esto abrirá tu navegador. Inicia sesión y autoriza el acceso. El script te mostrará tu `REFRESH_TOKEN`.

### 4B. Configurar variables de entorno

```bash
export GOOGLE_SHEETS_ID="YOUR_SPREADSHEET_ID"
export GOOGLE_CLIENT_ID="YOUR_CLIENT_ID.apps.googleusercontent.com"
export GOOGLE_CLIENT_SECRET="YOUR_CLIENT_SECRET"
export GOOGLE_REFRESH_TOKEN="YOUR_REFRESH_TOKEN"
export GOOGLE_SHEETS_WORKSHEET="Facturas"  # Opcional
```

---

## 5. Instalar dependencias

```bash
pip install -r requirements.txt
```

## 6. Probar la integración

```bash
python app.py
```

Si todo funciona bien, verás:
```
✅ Conexión exitosa con Google Sheets (Service Account)
```
o
```
✅ Conexión exitosa con Google Sheets (OAuth2)
```

## Estructura de datos en Google Sheets

| Campo | Descripción |
|-------|-------------|
| Timestamp | Fecha y hora de procesamiento |
| Empresa | Nombre de la empresa / razón social |
| RUC | Número RUC |
| Fecha | Fecha de la factura |
| Total | Monto total |
| Artículos | Lista de artículos (cantidad x descripción - precio) |
| Raw Data | JSON completo de la factura |

## Solución de problemas

### No se conecta a Google Sheets
```
No se encontraron credenciales de Google - Google Sheets deshabilitado
```
- Verifica que configuraste `GOOGLE_SHEETS_ID`
- Verifica que configuraste credenciales (Service Account O OAuth2)

### OAuth2: "Invalid refresh token"
- Ejecuta nuevamente: `python get_google_token.py`
- Asegúrate de haber autorizado el acceso

### "No tienes permiso"
- Para Service Account: comparte la hoja con el `client_email`
- Para OAuth2: asegúrate de usar la misma cuenta de Google

### Errores de API
- Verifica que activaste la API de Google Sheets en Google Cloud Console
- Verifica que tus credenciales tienen permisos suficientes

## Resumen de variables de entorno

| Variable | Tipo | Requerida |
|----------|------|-----------|
| GOOGLE_SHEETS_ID | String | Sí |
| GOOGLE_SHEETS_CREDENTIALS | JSON | Sí (Si usas Service Account) |
| GOOGLE_CLIENT_ID | String | Sí (Si usas OAuth2) |
| GOOGLE_CLIENT_SECRET | String | Sí (Si usas OAuth2) |
| GOOGLE_REFRESH_TOKEN | String | Sí (Si usas OAuth2) |
| GOOGLE_SHEETS_WORKSHEET | String | No (defecto: "Facturas") |

## Python version requerida
- Python 3.7 o superior
