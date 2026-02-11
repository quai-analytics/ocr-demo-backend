import os
import json
import base64
from flask import Flask, request, jsonify
from flask_cors import CORS
import joblib
import pandas as pd
from google.cloud import vision
import google.generativeai as genai
from sheets_service import sheets_service
from google.cloud import bigquery
from datetime import datetime

app = Flask(__name__)
CORS(app)  # Permitir requests desde el frontend

_model = None
_vision_client = None

ALLOWED_IMAGE_MIME_TYPES = {
    "image/png",
    "image/jpeg",
    "image/jpg",
    "image/webp",
    "image/tiff",
}


GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")


def get_vision_client():
    global _vision_client
    if _vision_client is None:
        _vision_client = vision.ImageAnnotatorClient()
    return _vision_client

def decode_base64(data: str) -> bytes:
    try:
        return base64.b64decode(data, validate=True)
    except Exception:
        return base64.b64decode(data)

def extract_json(text: str):
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1 and end > start:
            return json.loads(text[start:end + 1])
        raise

@app.get("/")
def health():
    return jsonify({"status": "ok"})

@app.post('/ocr/text')
def ocr_text():
    print("📥 Request recibida en /ocr/text")
    try:
        data = request.get_json(force=True)
        if not isinstance(data, dict):
            return jsonify({"error": "JSON inválido"}), 400

        base64_data = data.get("base64", "")
        mime_type = str(data.get("mimeType", "")).lower()

        if not base64_data:
            return jsonify({"error": "Falta base64"}), 400
        if mime_type not in ALLOWED_IMAGE_MIME_TYPES:
            return jsonify({"error": "Solo se aceptan imágenes (PNG, JPG, WEBP, TIFF)"}), 400

        content = decode_base64(base64_data)
        client = get_vision_client()
        image = vision.Image(content=content)
        response = client.document_text_detection(image=image)

        if response.error.message:
            return jsonify({"error": response.error.message}), 502

        text = response.full_text_annotation.text or ""
        return jsonify({"text": text})

    except Exception as e:
        return jsonify({"error": str(e)}), 400

@app.post('/ocr/structured')
def ocr_structured():
    print("📄 Recibida solicitud de OCR estructurado")
    try:
        data = request.get_json(force=True)
        if not isinstance(data, dict):
            return jsonify({"error": "JSON inválido"}), 400

        base64_data = data.get("base64", "")
        mime_type = str(data.get("mimeType", "")).lower()

        if not base64_data:
            return jsonify({"error": "Falta base64"}), 400
        if mime_type not in ALLOWED_IMAGE_MIME_TYPES:
            return jsonify({"error": "Solo se aceptan imágenes (PNG, JPG, WEBP, TIFF)"}), 400

        if not GEMINI_API_KEY:
            return jsonify({"error": "GEMINI_API_KEY no configurada"}), 500

        genai.configure(api_key=GEMINI_API_KEY)
        model = genai.GenerativeModel(GEMINI_MODEL)

        prompt = (
            "Extrae todos los datos de esta factura y responde SOLO con JSON válido. "
            "Usa este esquema: {"
            "\"empresa\":\"\",\"ruc\":\"\",\"fecha\":\"\",\"total\":\"\","
            "\"articulos\":[{\"cantidad\":\"\",\"descripcion\":\"\",\"precio\":\"\"}]}. "
            "Si no encuentras un campo, déjalo vacío."
        )

        image_part = {
            "mime_type": mime_type,
            "data": base64_data,
        }

        response = model.generate_content(
            [image_part, prompt],
            generation_config=genai.GenerationConfig(
                temperature=0.1,
                response_mime_type="application/json",
            ),
        )

        parsed = extract_json(response.text or "{}")
        
        # Enviar datos a Google Sheets automáticamente
        if sheets_service.is_connected() and parsed:
            sheets_service.send_invoice_data(parsed)
        
        print("✅ Datos extraídos y enviados a Google Sheets y BigQuery:", parsed)
        # Enviar datos a BigQuery automáticamente
        send_invoice_to_bigquery(parsed)
        
        return jsonify(parsed)

    except Exception as e:
        return jsonify({"error": str(e)}), 400

# Función para enviar datos a BigQuery
def send_invoice_to_bigquery(invoice_data):
    try:
        client = bigquery.Client()
        table_id = os.getenv("BIGQUERY_TABLE_ID", "tu-proyecto.ocr_facturas.facturas")
        row = {
            "timestamp": datetime.now().isoformat(),
            "empresa": invoice_data.get("empresa", ""),
            "ruc": invoice_data.get("ruc", ""),
            "fecha": invoice_data.get("fecha", ""),
            "total": invoice_data.get("total", ""),
            "articulos": json.dumps(invoice_data.get("articulos", [])),
            "raw_data": json.dumps(invoice_data)
        }
        errors = client.insert_rows_json(table_id, [row])
        if errors:
            print(f"❌ Error BigQuery: {errors}")
        else:
            print("✅ Datos enviados a BigQuery")
    except Exception as e:
        print(f"❌ Error enviando a BigQuery: {str(e)}")

if __name__ == '__main__':
    # Para pruebas locales: python app.py
    port = int(os.getenv("PORT", 8080))
    app.run(host='0.0.0.0', port=port, debug=True)
