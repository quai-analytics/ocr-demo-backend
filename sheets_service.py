import os
import gspread
from google.oauth2.service_account import Credentials
from google.oauth2 import service_account
from google.auth.transport.requests import Request
from typing import Dict, Any, List
from datetime import datetime
import json


class GoogleSheetsService:
    """Servicio para manejar la integración con Google Sheets"""
    
    def __init__(self):
        self.client = None
        self.spreadsheet = None
        self.worksheet = None
        self._initialize()
    
    def _initialize(self):
        """Inicializa la conexión con Google Sheets"""
        try:
            spreadsheet_id = os.getenv("GOOGLE_SHEETS_ID")
            worksheet_name = os.getenv("GOOGLE_SHEETS_WORKSHEET", "Facturas")
            
            if not spreadsheet_id:
                print("⚠️  GOOGLE_SHEETS_ID no configurada - Google Sheets deshabilitado")
                return
            
            # Intentar con Service Account JSON (desde variable de entorno o archivo)
            credentials_json = self._get_service_account_json()
            if credentials_json:
                self._initialize_with_service_account(credentials_json, spreadsheet_id, worksheet_name)
                return
            
            # Intentar con OAuth2 (Client ID + Secret)
            client_id = os.getenv("GOOGLE_CLIENT_ID")
            client_secret = os.getenv("GOOGLE_CLIENT_SECRET")
            refresh_token = os.getenv("GOOGLE_REFRESH_TOKEN")
            
            if client_id and client_secret and refresh_token:
                self._initialize_with_oauth2(client_id, client_secret, refresh_token, spreadsheet_id, worksheet_name)
                return
            
            print("⚠️  No se encontraron credenciales de Google - Google Sheets deshabilitado")
            print("   Configura: GOOGLE_SHEETS_CREDENTIALS (Service Account) O (GOOGLE_CLIENT_ID + GOOGLE_CLIENT_SECRET + GOOGLE_REFRESH_TOKEN)")
            
        except Exception as e:
            print(f"❌ Error inicializando Google Sheets: {str(e)}")
            self.client = None
    
    def _get_service_account_json(self) -> str:
        """Obtiene el JSON del service account desde variable de entorno o archivo"""
        # Primero intenta desde variable de entorno
        credentials_json = os.getenv("GOOGLE_SHEETS_CREDENTIALS")
        if credentials_json:
            return credentials_json
        
        # Si no, intenta leer desde archivo
        credential_files = [
            "/var/secrets/google/key.json",  # Cloud Run mounted secrets
            "/app/credentials.json",  # Local development
            "./credentials.json",
            "credentials.json"
        ]
        
        for filepath in credential_files:
            if os.path.exists(filepath):
                print(f"📂 Leyendo credenciales desde: {filepath}")
                try:
                    with open(filepath, 'r') as f:
                        return f.read()
                except Exception as e:
                    print(f"⚠️  Error leyendo {filepath}: {str(e)}")
        
        return None
    
    def _initialize_with_service_account(self, credentials_json, spreadsheet_id, worksheet_name):
        """Inicializa con Service Account"""
        try:
            print(f"🔍 Intentando parsear credenciales (primeros 100 chars): {credentials_json[:100]}...")
            
            # Intentar parsear el JSON
            try:
                credentials_dict = json.loads(credentials_json)
            except json.JSONDecodeError as e:
                print(f"❌ Error parseando JSON: {str(e)}")
                print(f"❌ JSON que se intentó parsear: {credentials_json}")
                raise ValueError(f"JSON inválido en GOOGLE_SHEETS_CREDENTIALS: {str(e)}")
            
            print(f"✓ JSON parseado exitosamente")
            print(f"✓ Campos encontrados: {list(credentials_dict.keys())}")
            
            scope = [
                'https://www.googleapis.com/auth/spreadsheets',
                'https://www.googleapis.com/auth/drive'
            ]
            credentials = Credentials.from_service_account_info(
                credentials_dict,
                scopes=scope
            )
            
            print(f"✓ Credenciales de Google creadas")
            
            self.client = gspread.authorize(credentials)
            print(f"✓ Cliente gspread autorizado")
            
            self.spreadsheet = self.client.open_by_key(spreadsheet_id)
            print(f"✓ Spreadsheet abierto: {spreadsheet_id}")
            
            try:
                self.worksheet = self.spreadsheet.worksheet(worksheet_name)
                print(f"✓ Hoja encontrada: {worksheet_name}")
            except gspread.exceptions.WorksheetNotFound:
                print(f"⚠️ Hoja no encontrada, creando: {worksheet_name}")
                self.worksheet = self.spreadsheet.add_worksheet(title=worksheet_name, rows=1000, cols=20)
                self._add_headers()
            
            print("✅ Conexión exitosa con Google Sheets (Service Account)")
            
        except Exception as e:
            print(f"❌ Error con Service Account: {str(e)}")
            import traceback
            print(f"❌ Traceback completo:\n{traceback.format_exc()}")
            raise
    
    def _initialize_with_oauth2(self, client_id, client_secret, refresh_token, spreadsheet_id, worksheet_name):
        """Inicializa con OAuth2 (Client ID + Secret)"""
        try:
            from google.oauth2.credentials import Credentials as OAuth2Credentials
            
            credentials = OAuth2Credentials(
                token=None,
                refresh_token=refresh_token,
                id_token=None,
                token_uri='https://oauth2.googleapis.com/token',
                client_id=client_id,
                client_secret=client_secret
            )
            
            # Refrescar el token
            request = Request()
            credentials.refresh(request)
            
            self.client = gspread.authorize(credentials)
            self.spreadsheet = self.client.open_by_key(spreadsheet_id)
            
            try:
                self.worksheet = self.spreadsheet.worksheet(worksheet_name)
            except gspread.exceptions.WorksheetNotFound:
                print(f"Creando nueva hoja: {worksheet_name}")
                self.worksheet = self.spreadsheet.add_worksheet(title=worksheet_name, rows=1000, cols=20)
                self._add_headers()
            
            print("✅ Conexión exitosa con Google Sheets (OAuth2)")
            
        except Exception as e:
            print(f"❌ Error con OAuth2: {str(e)}")
            raise
    
    def _add_headers(self):
        """Añade encabezados a la hoja"""
        if not self.worksheet:
            return
        
        headers = [
            "Timestamp",
            "Empresa",
            "RUC",
            "Fecha",
            "Total",
            "Artículos",
            "Raw Data"
        ]
        
        try:
            self.worksheet.append_row(headers)
            print("Encabezados añadidos a Google Sheets")
        except Exception as e:
            print(f"Error añadiendo encabezados: {str(e)}")
    
    def send_invoice_data(self, invoice_data: Dict[str, Any]) -> bool:
        """
        Envía datos de factura a Google Sheets
        
        Args:
            invoice_data: Diccionario con los datos de la factura
        
        Returns:
            True si fue exitoso, False en caso contrario
        """
        if not self.worksheet:
            print("❌ Google Sheets no inicializado - no hay conexión a worksheet")
            return False
        
        try:
            # Debug
            print(f"📝 Preparando datos para enviar a Google Sheets...")
            print(f"📊 Datos recibidos: {json.dumps(invoice_data, indent=2)}")
            
            # Preparar artículos como texto
            articulos = invoice_data.get("articulos", [])
            articulos_text = " | ".join([
                f"{a.get('cantidad', '')} x {a.get('descripcion', '')} - ${a.get('precio', '')}"
                for a in articulos
            ]) if articulos else ""
            
            # Crear fila de datos
            row = [
                datetime.now().isoformat(),
                invoice_data.get("empresa", ""),
                invoice_data.get("ruc", ""),
                invoice_data.get("fecha", ""),
                invoice_data.get("total", ""),
                articulos_text,
                json.dumps(invoice_data)
            ]
            
            print(f"📤 Enviando fila: {row[:3]}...")  # Debug: mostrar primeros 3 campos
            
            # Enviar a Google Sheets
            self.worksheet.append_row(row)
            print(f"✅ Datos enviados a Google Sheets: {invoice_data.get('empresa', 'N/A')}")
            return True
            
        except Exception as e:
            print(f"❌ Error enviando datos a Google Sheets: {str(e)}")
            print(f"📋 Tipo de error: {type(e).__name__}")
            import traceback
            print(f"📋 Traceback: {traceback.format_exc()}")
            return False
    
    def is_connected(self) -> bool:
        """Verifica si está conectado a Google Sheets"""
        return self.worksheet is not None


# Instancia global del servicio
sheets_service = GoogleSheetsService()
