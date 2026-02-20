import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
from datetime import datetime, timedelta
import plotly.express as px
import plotly.graph_objects as go
import time  # ← AGREGAR ESTO

# Configuración de la página
st.set_page_config(
    page_title="YapeChecker Dashboard",
    page_icon="💰",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ← AGREGAR ESTO: Auto-refresh cada 5 segundos
if 'last_refresh' not in st.session_state:
    st.session_state.last_refresh = time.time()

# Comprobar si han pasado 5 segundos
if time.time() - st.session_state.last_refresh > 1:
    st.session_state.last_refresh = time.time()
    st.rerun()

# Configuración de la página
st.set_page_config(
    page_title="YapeChecker Dashboard",
    page_icon="💰",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS personalizado
st.markdown("""
    <style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #722ED1;
        text-align: center;
        margin-bottom: 2rem;
    }
    .metric-card {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #722ED1;
    }
    </style>
""", unsafe_allow_html=True)

# Configuración de Google Sheets
SCOPES = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
SPREADSHEET_NAME = "YapeChecker_Pagos"

@st.cache_resource
def get_google_sheet():
    """Conecta con Google Sheets"""
    try:
        creds = ServiceAccountCredentials.from_json_keyfile_name('credentials.json', SCOPES)
        client = gspread.authorize(creds)
        sheet = client.open(SPREADSHEET_NAME).sheet1
        return sheet
    except Exception as e:
        st.error(f"Error conectando a Google Sheets: {e}")
        return None

def load_data():
    """Carga datos desde Google Sheets"""
    sheet = get_google_sheet()
    
    if sheet is None:
        return pd.DataFrame()
    
    try:
        # En lugar de get_all_records(), usar get_all_values()
        all_values = sheet.get_all_values()
        
        if len(all_values) < 2:  # No hay datos (solo header o vacío)
            return pd.DataFrame(columns=['Fecha', 'Hora', 'Monto', 'Remitente', 'Estado', 'Tienda'])
        
        # Primera fila es el header
        headers = all_values[0]
        data_rows = all_values[1:]
        
        # Crear DataFrame
        df = pd.DataFrame(data_rows, columns=headers)
        
        print(f"✅ DEBUG: DataFrame creado con {len(df)} filas")
        print(f"💰 DEBUG: Monto RAW: {df['Monto'].tolist()}")
        
        # Convertir Monto (puede venir como "0,1" con coma)
        df['Monto'] = df['Monto'].astype(str).str.replace(',', '.').astype(float)
        
        print(f"💰 DEBUG: Monto después de conversión: {df['Monto'].tolist()}")
        
        # Reemplazar tiendas vacías
        df['Tienda'] = df['Tienda'].replace('', 'Sin asignar')
        df['Tienda'] = df['Tienda'].fillna('Sin asignar')
        
        # Agregar columna Tienda si no existe en el sheet
        if 'Tienda' not in headers:
            # Actualizar el sheet con la nueva columna
            if len(df) > 0:
                current_header = sheet.row_values(1)
                if 'Tienda' not in current_header:
                    sheet.update_cell(1, len(current_header) + 1, 'Tienda')
                    for idx in range(len(df)):
                        sheet.update_cell(idx + 2, len(current_header) + 1, 'Sin asignar')
        
        return df
        
    except Exception as e:
        st.error(f"Error cargando datos: {e}")
        return pd.DataFrame()

def update_tienda(row_index, tienda):
    """Actualiza la tienda de un pago específico"""
    sheet = get_google_sheet()
    if sheet is None:
        return False
    
    try:
        # row_index es 0-based del DataFrame, pero en Sheets es 1-based + 1 (header)
        sheet_row = row_index + 2
        
        # Encontrar la columna de Tienda
        header = sheet.row_values(1)
        if 'Tienda' in header:
            tienda_col = header.index('Tienda') + 1
        else:
            # Si no existe la columna, crearla
            tienda_col = len(header) + 1
            sheet.update_cell(1, tienda_col, 'Tienda')
        
        # Actualizar la celda
        sheet.update_cell(sheet_row, tienda_col, tienda)
        return True
    except Exception as e:
        st.error(f"Error actualizando tienda: {e}")
        return False

def update_estado(row_index, estado):
    """Actualiza el estado de un pago específico"""
    sheet = get_google_sheet()
    if sheet is None:
        return False
    
    try:
        sheet_row = row_index + 2
        header = sheet.row_values(1)
        estado_col = header.index('Estado') + 1
        sheet.update_cell(sheet_row, estado_col, estado)
        return True
    except Exception as e:
        st.error(f"Error actualizando estado: {e}")
        return False

# Header
st.markdown('<div class="main-header">💰 YapeChecker Dashboard</div>', unsafe_allow_html=True)

# Sidebar
with st.sidebar:
    st.image("https://img.icons8.com/color/96/000000/money-circulation.png", width=100)
    st.title("Filtros")
    
    # Botón de actualizar
    if st.button("🔄 Actualizar datos", use_container_width=True):
        st.cache_resource.clear()
        st.rerun()
    
    st.divider()
    
    # Filtros
    fecha_desde = st.date_input(
        "Fecha desde",
        value=datetime.now() - timedelta(days=7)
    )
    
    fecha_hasta = st.date_input(
        "Fecha hasta",
        value=datetime.now()
    )
    
    st.divider()
    
    filtro_tienda = st.multiselect(
        "Filtrar por tienda",
        ["Tienda 1", "Tienda 2", "Sin asignar"],
        default=["Tienda 1", "Tienda 2", "Sin asignar"]
    )
    
    filtro_estado = st.multiselect(
        "Filtrar por estado",
        ["Pendiente", "Verificado", "Rechazado"],
        default=["Pendiente", "Verificado"]
    )

# Cargar datos
df = load_data()

if df.empty:
    st.info("📭 No hay pagos registrados todavía. Espera a que llegue el primer yapeo.")
else:
    # Convertir fecha a datetime para filtrar
    try:
        df['Fecha_dt'] = pd.to_datetime(df['Fecha'], format='%d/%m/%Y', errors='coerce')
    except:
        df['Fecha_dt'] = pd.to_datetime(df['Fecha'], errors='coerce')
    
    # Aplicar filtros
    mask = (
        (df['Fecha_dt'].dt.date >= fecha_desde) &
        (df['Fecha_dt'].dt.date <= fecha_hasta) &
        (df['Tienda'].isin(filtro_tienda)) &
        (df['Estado'].isin(filtro_estado))
    )
    df_filtrado = df[mask].copy()
    
    # Métricas principales
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        total_monto = df_filtrado['Monto'].sum()
        st.metric("💵 Total recaudado", f"S/ {total_monto:,.2f}")
    
    with col2:
        total_pagos = len(df_filtrado)
        st.metric("📊 Total de pagos", total_pagos)
    
    with col3:
        tienda1_monto = df_filtrado[df_filtrado['Tienda'] == 'Tienda 1']['Monto'].sum()
        st.metric("🏪 Tienda 1", f"S/ {tienda1_monto:,.2f}")
    
    with col4:
        tienda2_monto = df_filtrado[df_filtrado['Tienda'] == 'Tienda 2']['Monto'].sum()
        st.metric("🏬 Tienda 2", f"S/ {tienda2_monto:,.2f}")
    
    st.divider()
    
    # Gráficos
    col_graph1, col_graph2 = st.columns(2)
    
    with col_graph1:
        st.subheader("📈 Ventas por Tienda")
        tienda_data = df_filtrado.groupby('Tienda')['Monto'].sum().reset_index()
        if not tienda_data.empty:
            fig = px.pie(
                tienda_data, 
                values='Monto', 
                names='Tienda',
                color_discrete_sequence=['#722ED1', '#52C41A', '#FAAD14']
            )
            st.plotly_chart(fig, use_container_width=True)
    
    with col_graph2:
        st.subheader("📊 Estado de Pagos")
        estado_data = df_filtrado.groupby('Estado').size().reset_index(name='Cantidad')
        if not estado_data.empty:
            fig = px.bar(
                estado_data,
                x='Estado',
                y='Cantidad',
                color='Estado',
                color_discrete_sequence=['#FAAD14', '#52C41A', '#FF4D4F']
            )
            st.plotly_chart(fig, use_container_width=True)
    
    st.divider()
    
    # Tabla de pagos con edición
    st.subheader("📋 Gestión de Pagos")
    
    # Crear tabla editable
    for idx, row in df_filtrado.iterrows():
        with st.container():
            col1, col2, col3, col4, col5, col6, col7 = st.columns([1.5, 1, 1.5, 2, 1.5, 1.5, 1])
            
            with col1:
                st.text(f"📅 {row['Fecha']}")
            
            with col2:
                st.text(f"⏰ {row['Hora']}")
            
            with col3:
                st.text(f"💰 S/ {row['Monto']}")
            
            with col4:
                st.text(f"👤 {row['Remitente']}")
            
            with col5:
                # Dropdown para seleccionar tienda
                tienda_actual = row['Tienda'] if pd.notna(row['Tienda']) else 'Sin asignar'
                nueva_tienda = st.selectbox(
                    "Tienda",
                    ["Sin asignar", "Tienda 1", "Tienda 2"],
                    index=["Sin asignar", "Tienda 1", "Tienda 2"].index(tienda_actual),
                    key=f"tienda_{idx}",
                    label_visibility="collapsed"
                )
                
                if nueva_tienda != tienda_actual:
                    if update_tienda(idx, nueva_tienda):
                        st.success("✅", icon="✅")
                        st.rerun()
            
            with col6:
                # Dropdown para estado
                estado_actual = row['Estado'] if pd.notna(row['Estado']) else 'Pendiente'
                nuevo_estado = st.selectbox(
                    "Estado",
                    ["Pendiente", "Verificado", "Rechazado"],
                    index=["Pendiente", "Verificado", "Rechazado"].index(estado_actual),
                    key=f"estado_{idx}",
                    label_visibility="collapsed"
                )
                
                if nuevo_estado != estado_actual:
                    if update_estado(idx, nuevo_estado):
                        st.success("✅", icon="✅")
                        st.rerun()
            
            with col7:
                # Indicador visual de estado
                if row['Estado'] == 'Verificado':
                    st.success("✓")
                elif row['Estado'] == 'Rechazado':
                    st.error("✗")
                else:
                    st.warning("⏳")
            
            st.divider()
    
    # Exportar datos
    st.divider()
    col_exp1, col_exp2, col_exp3 = st.columns([2, 1, 1])
    
    with col_exp2:
        csv = df_filtrado.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 Descargar CSV",
            data=csv,
            file_name=f"yape_pagos_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv",
            use_container_width=True
        )
    
    with col_exp3:
        excel_buffer = pd.ExcelWriter('temp.xlsx', engine='xlsxwriter')
        df_filtrado.to_excel(excel_buffer, index=False)
        excel_buffer.close()
        
        with open('temp.xlsx', 'rb') as f:
            st.download_button(
                label="📥 Descargar Excel",
                data=f,
                file_name=f"yape_pagos_{datetime.now().strftime('%Y%m%d')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True
            )

# Footer
st.divider()
st.caption("💜 YapeChecker Dashboard - Hecho con Streamlit")