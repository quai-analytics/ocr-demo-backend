import os
import json
import base64
from flask import Flask, request, jsonify
from flask_cors import CORS
import joblib
import pandas as pd
from google.cloud import vision
import google.generativeai as genai

app = Flask(__name__)
CORS(app)  # Permitir requests desde el frontend

MODEL_PATH = os.getenv("MODEL_PATH", "real_estate_model_pipeline_v2.pkl")
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

# Cargar el modelo si existe
if os.path.exists(MODEL_PATH):
    try:
        _model = joblib.load(MODEL_PATH)
        print(f"Modelo cargado desde {MODEL_PATH}")
    except Exception as e:
        print(f"No se pudo cargar el modelo: {e}")
else:
    print(f"Aviso: no se encontró modelo en {MODEL_PATH}. Se usará predicción simulada.")

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

@app.post('/predict')
def predict():
    try:
        data = request.get_json(force=True)
        if not isinstance(data, dict):
            return jsonify({"error": "JSON inválido"}), 400

        # Si hay modelo, predecir con él
        if _model is not None:
            df = pd.DataFrame([data])
            y = float(_model.predict(df)[0])
            margin = float(os.getenv("MARGIN", "10000"))
            return jsonify({
                "estimated": y,
                "lowerBound": y - margin,
                "upperBound": y + margin,
            })

        # Fallback: predicción simulada coherente con el frontend
        bedrooms = int(data.get("bedrooms", 2))
        bathrooms = int(data.get("bathrooms", 2))
        size_m2 = float(data.get("size_m2", 120))
        parking_spaces = int(data.get("parking_spaces", 1))
        location = str(data.get("location", "")).strip()

        base = 150_000
        price_per_m2 = 2_000
        bedroom_val = bedrooms * 25_000
        bathroom_val = bathrooms * 15_000
        parking_val = parking_spaces * 10_000
        loc_mult = 1.3 if location == "Punta Pacífica" else 1.0
        estimated = round((base + size_m2 * price_per_m2 + bedroom_val + bathroom_val + parking_val) * loc_mult)
        margin = 10_000
        return jsonify({
            "estimated": float(estimated),
            "lowerBound": float(estimated - margin),
            "upperBound": float(estimated + margin),
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 400

@app.post('/ocr/text')
def ocr_text():
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
        return jsonify(parsed)

    except Exception as e:
        return jsonify({"error": str(e)}), 400

if __name__ == '__main__':
    # Para pruebas locales: python app.py
    port = int(os.getenv("PORT", 8080))
    app.run(host='0.0.0.0', port=port, debug=True)
