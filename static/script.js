const API_URL = '/api/payments';
let paymentsData = [];

// DOM Elements
const paymentsBody = document.getElementById('payments-body');
const totalAmountEl = document.getElementById('total-amount');
const tienda1AmountEl = document.getElementById('tienda1-amount');
const tienda2AmountEl = document.getElementById('tienda2-amount');
const totalCountEl = document.getElementById('total-count');
const searchInput = document.getElementById('search-input');
const filterStore = document.getElementById('filter-store');
const filterStatus = document.getElementById('filter-status');
const refreshBtn = document.getElementById('refresh-btn');
const pageTitleEl = document.getElementById('page-title');

// Navegación entre secciones (Pagos / Calculadora)
const sectionTitles = {
    pagos: 'Pagos Yape',
    calculadora: 'Calculadora de precios'
};

document.querySelectorAll('.nav-item[data-section]').forEach(item => {
    if (item.classList.contains('nav-item--disabled')) return;
    item.addEventListener('click', (e) => {
        e.preventDefault();
        const sectionId = item.dataset.section;
        if (!sectionId) return;
        document.querySelectorAll('.content-section').forEach(s => s.classList.remove('active'));
        document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));
        const section = document.getElementById('section-' + sectionId);
        if (section) {
            section.classList.add('active');
            item.classList.add('active');
            if (pageTitleEl && sectionTitles[sectionId]) pageTitleEl.textContent = sectionTitles[sectionId];
        }
    });
});

// Fetch Data
async function fetchPayments() {
    try {
        refreshBtn.classList.add('spin');
        const response = await fetch(API_URL);
        const result = await response.json();
        
        if (result.status === 'success') {
            paymentsData = Array.isArray(result.data) ? result.data : [];
            renderDashboard();
        }
    } catch (error) {
        console.error('Error fetching payments:', error);
    } finally {
        setTimeout(() => refreshBtn.classList.remove('spin'), 500);
    }
}

// Render Dashboard (Table + Metrics)
function renderDashboard() {
    const searchTerm = searchInput.value.toLowerCase();
    const storedFilter = filterStore.value;
    const statusFilter = filterStatus.value;

    const filteredData = paymentsData.filter(p => {
        const matchesSearch = p.Remitente.toLowerCase().includes(searchTerm);
        const matchesStore = storedFilter === 'all' || p.Tienda === storedFilter;
        const matchesStatus = statusFilter === 'all' || p.Estado === statusFilter;
        return matchesSearch && matchesStore && matchesStatus;
    });

    // Update Metrics
    updateMetrics(filteredData);

    // Update Table
    paymentsBody.innerHTML = '';
    // Sort by date/time desc (assuming simplified string sort for now, ideally parse dates)
    // Reverse needed because append_row adds to bottom
    [...filteredData].reverse().forEach(payment => {
        const row = document.createElement('tr');
        
        // ID Handling: If no ID, use a placeholder (shouldn't happen with new payments)
        const pid = payment.ID || 'legacy';
        const tiendaVal = payment.Tienda || 'Sin asignar';
        const estadoVal = payment.Estado || 'Pendiente';

        row.innerHTML = `
            <td>
                <div style="font-weight:bold">${payment.Hora}</div>
                <div style="font-size:0.8em; color:var(--text-secondary)">${payment.Fecha}</div>
            </td>
            <td style="font-weight:bold; color:var(--success)">S/ ${payment.Monto}</td>
            <td>${payment.Remitente}</td>
            <td>
                <select class="table-select" onchange="updatePayment('${pid}', 'tienda', this.value)">
                    <option value="Sin asignar" ${tiendaVal === 'Sin asignar' ? 'selected' : ''}>Sin asignar</option>
                    <option value="Tienda 1" ${tiendaVal === 'Tienda 1' ? 'selected' : ''}>Tienda 1</option>
                    <option value="Tienda 2" ${tiendaVal === 'Tienda 2' ? 'selected' : ''}>Tienda 2</option>
                </select>
            </td>
            <td>
                <select class="table-select badge-${estadoVal.toLowerCase()}" onchange="updatePayment('${pid}', 'estado', this.value)">
                    <option value="Pendiente" ${estadoVal === 'Pendiente' ? 'selected' : ''}>Pendiente</option>
                    <option value="Verificado" ${estadoVal === 'Verificado' ? 'selected' : ''}>Verificado</option>
                    <option value="Rechazado" ${estadoVal === 'Rechazado' ? 'selected' : ''}>Rechazado</option>
                </select>
            </td>
        `;
        paymentsBody.appendChild(row);
    });
}

// Update Metrics Logic
function updateMetrics(data) {
    const total = data.reduce((sum, p) => sum + (parseFloat(p.Monto) || 0), 0);
    const t1 = data.filter(p => p.Tienda === 'Tienda 1').reduce((sum, p) => sum + (parseFloat(p.Monto) || 0), 0);
    const t2 = data.filter(p => p.Tienda === 'Tienda 2').reduce((sum, p) => sum + (parseFloat(p.Monto) || 0), 0);

    totalAmountEl.innerText = total.toFixed(2);
    tienda1AmountEl.innerText = t1.toFixed(2);
    tienda2AmountEl.innerText = t2.toFixed(2);
    totalCountEl.innerText = data.length;
}

// Update Payment API Call
async function updatePayment(id, field, value) {
    if (id === 'legacy') {
        alert("No se pueden editar pagos antiguos sin ID. (Limpia el Sheet o genera IDs manualmente)");
        return;
    }

    const payload = {};
    payload[field] = value;

    try {
        const res = await fetch(`/api/payments/${id}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        
        if (!res.ok) throw new Error('Update failed');
        
        // Optimistic update logic could go here, but for now we just allow refresh to pick it up
        // or re-fetch immediately
        fetchPayments(); 
        
    } catch (err) {
        console.error(err);
        alert('Error al actualizar');
    }
}

// Event Listeners
searchInput.addEventListener('input', renderDashboard);
filterStore.addEventListener('change', renderDashboard);
filterStatus.addEventListener('change', renderDashboard);
refreshBtn.addEventListener('click', fetchPayments);

// Auto-refresh every 5s
setInterval(fetchPayments, 5000);

// Initial Load
fetchPayments();

// --- Vista previa de páginas (PDF.js) ---
if (typeof pdfjsLib !== 'undefined') {
    pdfjsLib.GlobalWorkerOptions.workerSrc = 'https://cdnjs.cloudflare.com/ajax/libs/pdf.js/2.16.105/pdf.worker.min.js';
}

let currentPdfDoc = null;
let currentFileUrl = null;

const previewThumbnails = document.getElementById('preview-thumbnails');
const previewEmpty = document.getElementById('preview-empty');
const previewMain = document.getElementById('preview-main');
const previewMainPlaceholder = document.getElementById('preview-main-placeholder');
const previewCanvas = document.getElementById('preview-canvas');
const previewImage = document.getElementById('preview-image');
const calcFileInput = document.getElementById('calc-file');

function clearPreview() {
    if (currentFileUrl) URL.revokeObjectURL(currentFileUrl);
    currentFileUrl = null;
    currentPdfDoc = null;
    if (previewThumbnails) {
        const toRemove = Array.from(previewThumbnails.children).filter(el => el.id !== 'preview-empty');
        toRemove.forEach(el => el.remove());
    }
    if (previewEmpty) previewEmpty.hidden = false;
    if (previewMainPlaceholder) { previewMainPlaceholder.hidden = false; previewMainPlaceholder.textContent = 'Seleccioná una página'; }
    if (previewCanvas) { previewCanvas.hidden = true; previewCanvas.getContext('2d')?.clearRect(0, 0, previewCanvas.width, previewCanvas.height); }
    if (previewImage) { previewImage.hidden = true; previewImage.src = ''; }
}

function showMainImage(src) {
    if (previewMainPlaceholder) previewMainPlaceholder.hidden = true;
    if (previewCanvas) previewCanvas.hidden = true;
    if (previewImage) {
        previewImage.src = src;
        previewImage.hidden = false;
    }
}

function showMainCanvas() {
    if (previewMainPlaceholder) previewMainPlaceholder.hidden = true;
    if (previewImage) previewImage.hidden = true;
    if (previewCanvas) previewCanvas.hidden = false;
}

async function renderPdfThumbnail(pageNum, pdfDoc, container) {
    const page = await pdfDoc.getPage(pageNum);
    const viewport = page.getViewport({ scale: 0.28 });
    const wrap = document.createElement('div');
    wrap.className = 'preview-thumb-wrap';
    const canvas = document.createElement('canvas');
    canvas.height = viewport.height;
    canvas.width = viewport.width;
    canvas.className = 'preview-thumb';
    const ctx = canvas.getContext('2d');
    await page.render({ canvasContext: ctx, viewport }).promise;
    const numSpan = document.createElement('span');
    numSpan.className = 'preview-thumb-num';
    numSpan.textContent = pageNum;
    wrap.appendChild(canvas);
    wrap.appendChild(numSpan);
    wrap.dataset.page = pageNum;
    wrap.addEventListener('click', () => selectPdfPage(pageNum, pdfDoc));
    container.appendChild(wrap);
}

function selectPdfPage(pageNum, pdfDoc) {
    previewThumbnails.querySelectorAll('.preview-thumb-wrap').forEach(el => el.classList.remove('active'));
    const wrap = previewThumbnails.querySelector(`[data-page="${pageNum}"]`);
    if (wrap) wrap.classList.add('active');
    if (!pdfDoc || !previewCanvas) return;
    pdfDoc.getPage(pageNum).then(async (page) => {
        const scale = 1.2;
        const viewport = page.getViewport({ scale });
        previewCanvas.height = viewport.height;
        previewCanvas.width = viewport.width;
        const ctx = previewCanvas.getContext('2d');
        await page.render({ canvasContext: ctx, viewport }).promise;
        showMainCanvas();
    });
}

async function loadPdfPreview(file) {
    clearPreview();
    const url = URL.createObjectURL(file);
    currentFileUrl = url;
    if (typeof pdfjsLib === 'undefined') {
        if (previewEmpty) { previewEmpty.hidden = false; previewEmpty.querySelector('p').textContent = 'Cargando PDF.js…'; }
        return;
    }
    try {
        const pdfDoc = await pdfjsLib.getDocument({ url }).promise;
        currentPdfDoc = pdfDoc;
        const numPages = pdfDoc.numPages;
        if (previewEmpty) previewEmpty.hidden = true;
        for (let i = 1; i <= numPages; i++) {
            await renderPdfThumbnail(i, pdfDoc, previewThumbnails);
        }
        selectPdfPage(1, pdfDoc);
    } catch (e) {
        console.error(e);
        if (previewEmpty) {
            previewEmpty.hidden = false;
            previewEmpty.querySelector('p').textContent = 'No se pudo cargar el PDF.';
        }
    }
}

function loadImagePreview(file) {
    clearPreview();
    const url = URL.createObjectURL(file);
    currentFileUrl = url;
    if (previewEmpty) previewEmpty.hidden = true;
    const wrap = document.createElement('div');
    wrap.className = 'preview-thumb-wrap';
    const img = document.createElement('img');
    img.src = url;
    img.className = 'preview-thumb active';
    img.alt = 'Página 1';
    const num = document.createElement('span');
    num.className = 'preview-thumb-num';
    num.textContent = '1';
    wrap.appendChild(img);
    wrap.appendChild(num);
    wrap.addEventListener('click', () => {
        previewThumbnails.querySelectorAll('.preview-thumb-wrap').forEach(el => el.classList.remove('active'));
        wrap.classList.add('active');
        previewImage.src = url;
        previewImage.hidden = false;
        if (previewCanvas) previewCanvas.hidden = true;
        if (previewMainPlaceholder) previewMainPlaceholder.hidden = true;
    });
    previewThumbnails.appendChild(wrap);
    previewImage.src = url;
    previewImage.hidden = false;
    if (previewCanvas) previewCanvas.hidden = true;
    if (previewMainPlaceholder) previewMainPlaceholder.hidden = true;
}

function loadOfficePlaceholder(filename) {
    clearPreview();
    if (previewEmpty) {
        previewEmpty.hidden = false;
        previewEmpty.querySelector('p').textContent = 'Vista previa no disponible';
        const sm = previewEmpty.querySelector('small');
        if (sm) sm.textContent = 'Word, Excel o PPT. Se verá el resultado al calcular.';
    }
    if (previewMainPlaceholder) {
        previewMainPlaceholder.hidden = false;
        previewMainPlaceholder.textContent = 'Subí PDF o imagen para ver páginas aquí.';
    }
}

if (calcFileInput) {
    calcFileInput.addEventListener('change', function () {
        const file = this.files && this.files[0];
        if (!file) { clearPreview(); return; }
        const name = (file.name || '').toLowerCase();
        const type = file.type || '';
        if (type === 'application/pdf' || name.endsWith('.pdf')) {
            loadPdfPreview(file);
        } else if (type.startsWith('image/') || /\.(png|jpe?g)$/.test(name)) {
            loadImagePreview(file);
        } else {
            loadOfficePlaceholder(file.name);
        }
    });
}

// --- Calculadora de precios ---
const calculatorForm = document.getElementById('calculator-form');
const calcResult = document.getElementById('calc-result');
const calcError = document.getElementById('calc-error');
const calcLoading = document.getElementById('calc-loading');
const calcTotalValue = document.getElementById('calc-total-value');
const calcDesglose = document.getElementById('calc-desglose');
const btnCalcular = document.getElementById('btn-calcular');

if (calculatorForm) {
    calculatorForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const fileInput = document.getElementById('calc-file');
        if (!fileInput || !fileInput.files.length) {
            showCalcError('Elegí un archivo.');
            return;
        }
        const file = fileInput.files[0];
        const formData = new FormData();
        formData.append('file', file);
        formData.append('ambos_lados', document.getElementById('opt-ambos-lados').checked ? 'true' : 'false');
        formData.append('anillado', document.getElementById('opt-anillado').checked ? 'true' : 'false');
        formData.append('a_tinta', document.getElementById('opt-tinta').checked ? 'true' : 'false');

        if (calcResult) calcResult.hidden = true;
        if (calcError) { calcError.hidden = true; calcError.textContent = ''; }
        if (calcLoading) calcLoading.hidden = false;
        if (btnCalcular) btnCalcular.disabled = true;

        try {
            const res = await fetch('/api/calculate-price', {
                method: 'POST',
                body: formData
            });
            const data = await res.json().catch(() => ({}));
            if (calcLoading) calcLoading.hidden = true;
            if (btnCalcular) btnCalcular.disabled = false;

            if (!res.ok) {
                const errMsg = Array.isArray(data.detail) ? data.detail.map(d => d.msg || d).join(' ') : (data.detail || data.message || 'Error al calcular');
                showCalcError(errMsg);
                return;
            }
            if (data.status === 'success' && data.total !== undefined) {
                if (calcTotalValue) calcTotalValue.textContent = Number(data.total).toFixed(2);
                if (calcDesglose) calcDesglose.textContent = data.desglose || '';
                if (calcResult) calcResult.hidden = false;
            } else {
                showCalcError(data.detail || data.message || 'Respuesta inesperada');
            }
        } catch (err) {
            if (calcLoading) calcLoading.hidden = true;
            if (btnCalcular) btnCalcular.disabled = false;
            showCalcError('Error de conexión. ¿Está corriendo el servidor?');
        }
    });
}

function showCalcError(msg) {
    const el = document.getElementById('calc-error');
    if (el) { el.textContent = msg; el.hidden = false; }
}
