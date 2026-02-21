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
