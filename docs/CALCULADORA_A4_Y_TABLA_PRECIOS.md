# Calculadora A4 y tabla de precios — Copy-on

## 1. Logo en el sidebar

- Se reemplazó el texto "COPY on" por la imagen **LogoCopyOn.png** en el sidebar.
- La ruta usada es `images/LogoCopyOn.png` (desde la carpeta `static/`). Si no ves el logo, revisa que el archivo esté en `static/images/LogoCopyOn.png` y recarga con Ctrl+Shift+R.

---

## 2. Tabla de precios — base en Excel/CSV

Hay un archivo base en **`data/tabla_precios_A4_base.csv`** que puedes abrir en Excel, editar y usar como referencia.

### Resumen de lo que definiste (A4)

| Tipo | Condición | Precio (S/) |
|------|-----------|-------------|
| **B/N 1 cara** | normal (≤50 págs) | 0.30 por página |
| **B/N 1 cara** | al por mayor (>50 págs) | 0.20 por página |
| **B/N 2 caras** | — | 0.15 por página |
| **Color** | mínimo (poco color) | 0.40 por hoja |
| **Color** | máximo (lleno) | 1.00 por hoja |
| **Color** | media hoja con color | 0.60–0.70 (referencia 0.65) |

**Notas que comentaste:**

- **DNI / mucho negro:** más consumo de tinta/tóner; se podría subir un % pero a veces lo cobras igual (0.30). Se puede dejar como regla opcional más adelante (ej. “hojas muy negras” con umbral en visión).
- **Anillados:** tienen tabla pero no fija; se puede añadir una columna o una hoja aparte en el Excel cuando la tengan definida.

---

## 3. Ecuación para color “al por mayor” con visión computacional

La idea es usar el **porcentaje de color por hoja** (`color_pct` que ya calcula el backend con OpenCV) para:

1. **Por hoja:** interpolar entre mínimo (0.40) y máximo (1.00) según `color_pct`.
2. **Al por mayor (varias hojas):** promediar el `color_pct` de las hojas (o sumar “color total”) y aplicar un descuento por volumen.

### Propuesta de ecuación por hoja (A4 color)

- `color_pct` = 0–100 (lo que devuelve `/api/analyze-page`).
- Precio por hoja (entre 0.40 y 1.00):

  **precio_hoja = 0.40 + (1.00 - 0.40) × (color_pct / 100)**

  Es decir: **precio_hoja = 0.40 + 0.60 × (color_pct / 100)**.

- Ejemplos:
  - color_pct = 0   → 0.40 (mínimo)
  - color_pct = 50  → 0.70 (media hoja)
  - color_pct = 100 → 1.00 (lleno)

Podéis ajustar la curva (por ejemplo que “poco color” suba más lento) usando un exponente:  
`precio_hoja = 0.40 + 0.60 × (color_pct / 100)^k` con `k` &lt; 1 para suavizar.

### Propuesta “al por mayor” (varias hojas A4 color)

- Opción A — **descuento por cantidad:**  
  Calcular precio por hoja como arriba para cada hoja (o promedio de `color_pct`), sumar, y aplicar un descuento según cantidad (ej. &gt;20 hojas → 5%, &gt;50 → 10%). Los % los definís vosotros en el Excel.

- Opción B — **precio promedio ponderado:**  
  Promedio de `color_pct` de todas las hojas → un solo `color_pct_avg` → aplicar la ecuación de arriba una vez y multiplicar por número de hojas. Luego opcionalmente descuento por volumen.

La calculadora con visión puede: para cada página subida (o cada imagen de un PDF), llamar a `/api/analyze-page`, obtener `color_pct`, y luego en el front (o en el backend) aplicar esta ecuación y la tabla de tramos.

---

## 4. Comentarios sobre la calculadora A4

- **Empezar solo con A4** está bien: se puede tener tamaño fijo A4 y opciones 1 cara / 2 caras, B/N vs color, cantidad de páginas y, para color, subida de imágenes para análisis.
- **B/N:** la lógica es directa: tramo 1–50 → 0.30; 51+ → 0.20 (1 cara); 2 caras → 0.15. No hace falta visión para B/N a menos que más adelante quieras detectar “hojas muy negras” (DNI) y aplicar un recargo.
- **Color:** aquí encaja la visión: subir imagen(s) de página → backend devuelve `color_pct` (y opcionalmente `tier`) → en la calculadora aplicamos la ecuación (0.40 + 0.60 × color_pct/100) y, si hay varias hojas, la regla de “al por mayor” que elijáis (descuento por cantidad o promedio ponderado).
- **Excel como base:** el CSV en `data/` puede ser la “fuente de verdad” que tu mamá edita (precios, tramos, notas). Luego se puede cargar ese CSV en el backend o copiar los valores a la app para no duplicar datos.

Si quieres, el siguiente paso puede ser: (1) implementar en la calculadora la lógica A4 (B/N + color con la ecuación) usando el CSV o valores fijos, o (2) afinar la ecuación (por ejemplo el exponente `k` o los tramos de descuento por mayor).
