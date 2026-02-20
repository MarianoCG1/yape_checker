from fastapi import FastAPI, HTTPException, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from datetime import datetime
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import logging
import uuid
import os

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="YapeChecker API")

# CORS para permitir requests desde la app Android y Web
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Modelo de datos para un pago
class Payment(BaseModel):
    monto: float
    remitente: str
    fecha: str
    hora: str
    id: str = None # Opcional al recibir, se genera si no existe

# Modelo para actualizar pago
class PaymentUpdate(BaseModel):
    tienda: str = None
    estado: str = None

# Configuración de Google Sheets
SCOPES = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
SPREADSHEET_NAME = "YapeChecker_Pagos"

def get_google_sheet():
    """Conecta con Google Sheets"""
    try:
        creds = ServiceAccountCredentials.from_json_keyfile_name('credentials.json', SCOPES)
        client = gspread.authorize(creds)
        sheet = client.open(SPREADSHEET_NAME).sheet1
        return sheet
    except Exception as e:
        logger.error(f"Error conectando a Google Sheets: {e}")
        return None

# Servir archivos estáticos (Frontend)
static_dir = os.path.join(os.path.dirname(__file__), "static")
if not os.path.exists(static_dir):
    os.makedirs(static_dir)
app.mount("/static", StaticFiles(directory=static_dir), name="static")

@app.get("/")
def read_root():
    """Redirige al dashboard"""
    from starlette.responses import RedirectResponse
    return RedirectResponse(url="/static/index.html")

@app.get("/health")
def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

@app.post("/api/payment")
async def receive_payment(payment: Payment):
    """Recibe un pago, le asigna ID y lo guarda"""
    try:
        # Generar ID único si no viene
        payment_id = str(uuid.uuid4())
        
        logger.info(f"Pago recibido: {payment.model_dump()}")
        
        sheet = get_google_sheet()
        
        if sheet is None:
            # Fallback local/log
            return {"status": "logged", "id": payment_id, "message": "Sheets offline, logueado"}
        
        # Verificar cabeceras para asegurar columna ID
        headers = sheet.row_values(1)
        if "ID" not in headers:
            sheet.update_cell(1, len(headers) + 1, "ID")
            sheet.update_cell(1, len(headers) + 2, "Tienda") # Asegurar Tienda también
        
        # Preparar datos
        # Orden esperado: Fecha, Hora, Monto, Remitente, Estado, Tienda, ID
        # Nota: Ajusta esto según tus columnas reales en Sheets
        
        row_data = [
            payment.fecha,
            payment.hora,
            payment.monto,
            payment.remitente,
            "Pendiente",    # Estado
            "Sin asignar",  # Tienda
            payment_id      # ID
        ]
        
        sheet.append_row(row_data)
        
        return {"status": "success", "id": payment_id, "message": "Pago registrado"}
        
    except Exception as e:
        logger.error(f"Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/payments")
def get_payments():
    """Obtiene todos los pagos como lista de dicts"""
    try:
        sheet = get_google_sheet()
        if not sheet:
            raise HTTPException(status_code=503, detail="Unavailable")
            
        records = sheet.get_all_records()
        # Asegurar que todos tengan ID (para registros viejos)
        # Esto es lento pero necesario para la transición
        return {"status": "success", "data": records}
    except Exception as e:
        logger.error(f"Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/api/payments/{payment_id}")
async def update_payment(payment_id: str, update: PaymentUpdate):
    """Actualiza estado o tienda de un pago por ID"""
    try:
        sheet = get_google_sheet()
        if not sheet:
            raise HTTPException(status_code=503, detail="Unavailable")
            
        # Buscar la celda con el ID
        # Asumimos que ID está en la columna G (7) o similar. 
        # get_all_records es costoso par buscar, mejor usamos find
        try:
            cell = sheet.find(payment_id)
        except gspread.exceptions.CellNotFound:
            raise HTTPException(status_code=404, detail="Pago no encontrado")
            
        row = cell.row
        
        # Actualizar campos
        if update.tienda:
            # Buscar columna Tienda
            headers = sheet.row_values(1)
            try:
                col_idx = headers.index("Tienda") + 1
                sheet.update_cell(row, col_idx, update.tienda)
            except ValueError:
                pass # No existe columna Tienda
                
        if update.estado:
            # Buscar columna Estado
            headers = sheet.row_values(1)
            try:
                col_idx = headers.index("Estado") + 1
                sheet.update_cell(row, col_idx, update.estado)
            except ValueError:
                pass

        return {"status": "success", "message": "Actualizado"}
        
    except Exception as e:
        logger.error(f"Error update: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    import socket
    
    hostname = socket.gethostname()
    local_ip = socket.gethostbyname(hostname)
    
    print(f"Server at http://{local_ip}:8000")
    uvicorn.run(app, host="0.0.0.0", port=8000)
