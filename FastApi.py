from fastapi import FastAPI, HTTPException, Body, File, UploadFile, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from datetime import datetime
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import json
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
    """Conecta con Google Sheets.

    En producción (Render y similares) no hay archivo persistente, así que
    la credencial se lee de la variable de entorno GOOGLE_CREDENTIALS_JSON
    (el contenido completo de credentials.json, pegado como texto). En
    desarrollo local, si esa variable no está, cae al archivo
    credentials.json (gitignoreado, nunca se sube al repo).
    """
    try:
        raw_creds = os.environ.get("GOOGLE_CREDENTIALS_JSON")
        if raw_creds:
            creds_dict = json.loads(raw_creds)
            creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, SCOPES)
        else:
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
        
        # Verificar cabeceras para asegurar columnas ID y Tienda (cada una por
        # separado -- agregar ambas sin chequear individualmente duplicaba
        # "Tienda" si ya existía, rompiendo get_all_records más adelante).
        headers = sheet.row_values(1)
        next_col = len(headers) + 1
        if "ID" not in headers:
            sheet.update_cell(1, next_col, "ID")
            next_col += 1
        if "Tienda" not in headers:
            sheet.update_cell(1, next_col, "Tienda")
            next_col += 1
        
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

# Orden real de columnas escritas por receive_payment() -- se usa acá para
# leer por posición en vez de por nombre de encabezado, así una fila de
# headers desprolija (ej. "Tienda" duplicado) nunca rompe la lectura.
COLUMN_ORDER = ["Fecha", "Hora", "Monto", "Remitente", "Estado", "Tienda", "ID"]


@app.get("/api/payments")
def get_payments():
    """Obtiene todos los pagos como lista de dicts, leyendo por posición de
    columna (no por nombre de encabezado -- inmune a headers duplicados)."""
    try:
        sheet = get_google_sheet()
        if not sheet:
            raise HTTPException(status_code=503, detail="Unavailable")

        all_values = sheet.get_all_values()
        rows = all_values[1:] if len(all_values) > 1 else []  # saltar encabezados
        records = []
        for row in rows:
            record = {}
            for i, col_name in enumerate(COLUMN_ORDER):
                record[col_name] = row[i] if i < len(row) else ""
            records.append(record)

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


# --- Calculadora de precios (Copy-on) ---
def _get_page_count_and_images(data: bytes, filename: str, content_type: str):
    """Devuelve (num_pages, list_of_image_bytes) para PDF/imagen; para Office devuelve (num_pages, None) sin imágenes."""
    ext = (filename or "").lower().split(".")[-1]
    if ext == "pdf" or (content_type or "").startswith("application/pdf"):
        try:
            import fitz  # PyMuPDF
            doc = fitz.open(stream=data, filetype="pdf")
            pages = []
            for i in range(len(doc)):
                page = doc.load_page(i)
                pix = page.get_pixmap(dpi=150)
                img_bytes = pix.tobytes("png")
                pages.append(img_bytes)
            doc.close()
            return len(pages), pages
        except Exception as e:
            logger.exception("Error leyendo PDF")
            raise ValueError(f"No se pudo leer el PDF: {e}")
    if ext in ("png", "jpg", "jpeg") or (content_type or "").startswith("image/"):
        return 1, [data]
    if ext in ("docx", "doc"):
        try:
            from docx import Document
            from io import BytesIO
            doc = Document(BytesIO(data))
            # Estimación: ~1 página cada 20 párrafos
            n = max(1, len(doc.paragraphs) // 20 + 1)
            return n, None
        except Exception as e:
            logger.exception("Error leyendo Word")
            raise ValueError(f"No se pudo leer el Word: {e}")
    if ext in ("xlsx", "xls"):
        try:
            import openpyxl
            from io import BytesIO
            wb = openpyxl.load_workbook(BytesIO(data), read_only=True)
            n = len(wb.sheetnames)
            wb.close()
            return max(1, n), None
        except Exception as e:
            logger.exception("Error leyendo Excel")
            raise ValueError(f"No se pudo leer el Excel: {e}")
    if ext in ("pptx", "ppt"):
        try:
            from pptx import Presentation
            from io import BytesIO
            prs = Presentation(BytesIO(data))
            n = len(prs.slides)
            return max(1, n), None
        except Exception as e:
            logger.exception("Error leyendo PowerPoint")
            raise ValueError(f"No se pudo leer el PowerPoint: {e}")
    raise ValueError("Formato no soportado. Use PDF, Word, Excel, PowerPoint o imagen.")


@app.post("/api/calculate-price")
async def calculate_price(
    file: UploadFile = File(...),
    ambos_lados: str = Form("false"),
    anillado: str = Form("false"),
    a_tinta: str = Form("true"),
):
    """
    Sube un archivo (PDF, Word, Excel, PPT o imagen) y opciones para calcular el precio A4.
    Opciones: por ambos lados, anillado, a tinta.
    """
    try:
        data = await file.read()
        if not data:
            raise HTTPException(status_code=400, detail="Archivo vacío")
        opts_ambos = ambos_lados.lower() == "true"
        opts_anillado = anillado.lower() == "true"
        opts_tinta = a_tinta.lower() == "true"

        num_pages, image_list = _get_page_count_and_images(data, file.filename or "", file.content_type or "")

        # Precios A4 (por ahora fijos; luego desde CSV/Excel)
        PRECIO_BN_UNA_CARA = 0.30
        PRECIO_BN_AMBOS = 0.15
        PRECIO_BN_MAYOR = 0.20
        PRECIO_COLOR_MIN = 0.40
        PRECIO_COLOR_MAX = 1.00
        ANILLADO_FIJO = 2.00

        total = 0.0
        lineas = []

        if opts_ambos:
            # Por ambos lados: 0.15 por página (B/N)
            precio_pag = PRECIO_BN_AMBOS
            if num_pages > 50:
                precio_pag = PRECIO_BN_AMBOS  # mismo por mayor
            total = round(precio_pag * num_pages, 2)
            lineas.append(f"{num_pages} páginas × S/ {precio_pag:.2f} (ambos lados B/N) = S/ {total:.2f}")
        elif image_list is not None and opts_tinta:
            # Tenemos imágenes: análisis de color por página (PDF o imagen)
            from color_analysis import analyze_image
            for i, img_bytes in enumerate(image_list):
                anal = analyze_image(img_bytes)
                color_pct = anal.get("color_pct", 0) or 0
                precio_hoja = PRECIO_COLOR_MIN + (PRECIO_COLOR_MAX - PRECIO_COLOR_MIN) * (color_pct / 100.0)
                total += round(precio_hoja, 2)
                lineas.append(f"Pág {i+1}: color {color_pct:.1f}% → S/ {precio_hoja:.2f}")
        else:
            # Sin imágenes (Office) o sin tinta: precio B/N por página
            precio_pag = PRECIO_BN_UNA_CARA
            if num_pages > 50:
                precio_pag = PRECIO_BN_MAYOR
            total = round(precio_pag * num_pages, 2)
            lineas.append(f"{num_pages} páginas × S/ {precio_pag:.2f} (B/N estimado) = S/ {total:.2f}")
            if image_list is None:
                lineas.append("(Sube PDF o imagen para cálculo con análisis de color.)")

        if opts_anillado:
            total = round(total + ANILLADO_FIJO, 2)
            lineas.append(f"Anillado: S/ {ANILLADO_FIJO:.2f}")

        desglose = "\n".join(lineas)
        return {"status": "success", "total": total, "desglose": desglose, "num_pages": num_pages}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception("Error en calculate-price")
        raise HTTPException(status_code=500, detail=str(e))


# --- Análisis de color por página (Copy-on calculadora) ---
@app.post("/api/analyze-page")
async def analyze_page(file: UploadFile = File(...)):
    """
    Sube una imagen de una página (PNG/JPEG) y devuelve análisis de uso de color:
    color_pct (0-100), tier (bajo/medio/alto), saturación y aproximación CMYK.
    Para usar en la calculadora de precios por impresión.
    """
    try:
        content_type = file.content_type or ""
        if "image/" not in content_type:
            raise HTTPException(
                status_code=400,
                detail="Solo se aceptan imágenes (image/png, image/jpeg, etc.)",
            )
        data = await file.read()
        if not data:
            raise HTTPException(status_code=400, detail="Archivo vacío")
        from color_analysis import analyze_image

        result = analyze_image(data)
        return {"status": "success", "analysis": result}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception("Error en análisis de página")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    import socket
    
    hostname = socket.gethostname()
    local_ip = socket.gethostbyname(hostname)
    
    print(f"Server at http://{local_ip}:8000")
    uvicorn.run(app, host="0.0.0.0", port=8000)
