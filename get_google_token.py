#!/usr/bin/env python3
"""
Script para generar credenciales OAuth2 de Google.
Esto genera un REFRESH_TOKEN que puedes usar en lugar de Service Account.

Uso:
    python get_google_token.py --client-id YOUR_CLIENT_ID --client-secret YOUR_CLIENT_SECRET
"""

import os
import sys
import json
import argparse
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive'
]

def get_token(client_id, client_secret):
    """Genera el refresh token usando OAuth2"""
    
    # Crear la configuración
    client_config = {
        "installed": {
            "client_id": client_id,
            "client_secret": client_secret,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": ["urn:ietf:wg:oauth:2.0:oob"]
        }
    }
    
    # Crear el flujo
    flow = InstalledAppFlow.from_client_config(
        client_config,
        scopes=SCOPES
    )
    
    # Ejecutar el flujo localmente (abrirá el navegador)
    print("🔐 Abriendo navegador para autenticación...")
    print("📝 Por favor, inicia sesión con tu cuenta de Google")
    print("⚠️  Se pedirá permiso para acceder a Google Sheets y Drive\n")
    
    credentials = flow.run_local_server(port=0)
    
    # Mostrar el refresh token
    print("\n✅ ¡Autenticación exitosa!\n")
    print("=" * 60)
    print("REFRESH TOKEN (guarda esto en tu .env):")
    print("=" * 60)
    print(credentials.refresh_token)
    print("=" * 60)
    print("\nVariables de entorno a configurar:")
    print(f"export GOOGLE_CLIENT_ID='{client_id}'")
    print(f"export GOOGLE_CLIENT_SECRET='{client_secret}'")
    print(f"export GOOGLE_REFRESH_TOKEN='{credentials.refresh_token}'")
    print("=" * 60)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Generar credenciales OAuth2 de Google')
    parser.add_argument('--client-id', required=True, help='Google Client ID')
    parser.add_argument('--client-secret', required=True, help='Google Client Secret')
    
    args = parser.parse_args()
    
    get_token(args.client_id, args.client_secret)
