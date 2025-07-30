// Global variables
let currentPage = 1;
let currentTab = 'vehicles';
let currentStatus = 'active';

// DOM elements
const loadingModal = document.getElementById('loadingModal');
const runScrapingBtn = document.getElementById('runScrapingBtn');
const scrapingStatus = document.getElementById('scrapingStatus');
const searchInput = document.getElementById('searchInput');
const statusFilter = document.getElementById('statusFilter');
const searchBtn = document.getElementById('searchBtn');

// Initialize the application
document.addEventListener('DOMContentLoaded', function() {
    initializeTabs();
    loadStats();
    loadVehicles();
    checkScrapingStatus();

    // Set up event listeners
    runScrapingBtn.addEventListener('click', runScraping);
    searchBtn.addEventListener('click', performSearch);
    statusFilter.addEventListener('change', function() {
        currentStatus = this.value;
        currentPage = 1;
        loadVehicles();
    });

    searchInput.addEventListener('keypress', function(e) {
        if (e.key === 'Enter') {
            performSearch();
        }
    });

    // Check scraping status periodically
    setInterval(checkScrapingStatus, 5000);
});

// Tab functionality
function initializeTabs() {
    const tabBtns = document.querySelectorAll('.tab-btn');
    const tabContents = document.querySelectorAll('.tab-content');

    tabBtns.forEach(btn => {
        btn.addEventListener('click', function() {
            const tabName = this.dataset.tab;

            // Update active tab button
            tabBtns.forEach(b => {
                b.classList.remove('active', 'border-blue-500', 'text-blue-600');
                b.classList.add('border-transparent', 'text-gray-500');
            });
            this.classList.add('active', 'border-blue-500', 'text-blue-600');
            this.classList.remove('border-transparent', 'text-gray-500');

            // Show/hide tab content
            tabContents.forEach(content => content.classList.add('hidden'));
            document.getElementById(tabName + 'Tab').classList.remove('hidden');

            currentTab = tabName;

            // Load appropriate data
            if (tabName === 'vehicles') {
                loadVehicles();
            } else if (tabName === 'recent') {
                loadRecentVehicles();
            } else if (tabName === 'removed') {
                loadRemovedVehicles();
            }
        });
    });
}

// API functions
async function apiCall(endpoint, options = {}) {
    try {
        showLoading();
        const response = await fetch(`/api${endpoint}`, {
            headers: {
                'Content-Type': 'application/json',
                ...options.headers
            },
            ...options
        });

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        return await response.json();
    } catch (error) {
        console.error('API call failed:', error);
        showError('Erro ao carregar dados: ' + error.message);
        return null;
    } finally {
        hideLoading();
    }
}

// Load statistics
async function loadStats() {
    const stats = await apiCall('/vehicles/stats');
    if (stats) {
        document.getElementById('statsActive').textContent = stats.total_active;
        document.getElementById('statsSold').textContent = stats.total_sold;
        document.getElementById('statsRemoved').textContent = stats.total_removed;
        document.getElementById('statsAdded24h').textContent = stats.added_last_24h;
        document.getElementById('statsRemoved24h').textContent = stats.removed_last_24h;
    }
}

// Load vehicles
async function loadVehicles() {
    const params = new URLSearchParams({
        page: currentPage,
        per_page: 20,
        status: currentStatus
    });

    const data = await apiCall(`/vehicles?${params}`);
    if (data) {
        renderVehicles(data.vehicles, 'vehiclesList');
        renderPagination(data.current_page, data.pages);
    }
}

// Load recent vehicles
async function loadRecentVehicles() {
    const vehicles = await apiCall('/vehicles/recent');
    if (vehicles) {
        renderVehicles(vehicles, 'recentVehiclesList');
    }
}

// Load removed vehicles
async function loadRemovedVehicles() {
    const vehicles = await apiCall('/vehicles/removed');
    if (vehicles) {
        renderVehicles(vehicles, 'removedVehiclesList');
    }
}

// Perform search
async function performSearch() {
    const query = searchInput.value.trim();
    if (!query) {
        loadVehicles();
        return;
    }

    const vehicles = await apiCall(`/vehicles/search?q=${encodeURIComponent(query)}`);
    if (vehicles) {
        renderVehicles(vehicles, 'vehiclesList');
        document.getElementById('pagination').innerHTML = '';
    }
}

// Render vehicles
function renderVehicles(vehicles, containerId) {
    const container = document.getElementById(containerId);

    if (!vehicles || vehicles.length === 0) {
        container.innerHTML = `
            <div class="text-center py-8">
                <i class="fas fa-car text-gray-400 text-4xl mb-4"></i>
                <p class="text-gray-500">Nenhum veículo encontrado</p>
            </div>
        `;
        return;
    }

    container.innerHTML = vehicles.map(vehicle => `
        <div class="border border-gray-200 rounded-lg p-4 card-hover">
            <div class="flex justify-between items-start">
                <div class="flex-1">
                    <h3 class="text-lg font-semibold text-gray-900 mb-2">${vehicle.title}</h3>
                    <div class="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm text-gray-600">
                        ${vehicle.brand ? `<div><i class="fas fa-tag mr-1"></i>${vehicle.brand}</div>` : ''}
                        ${vehicle.year ? `<div><i class="fas fa-calendar mr-1"></i>${vehicle.year}</div>` : ''}
                        ${vehicle.mileage ? `<div><i class="fas fa-tachometer-alt mr-1"></i>${vehicle.mileage}</div>` : ''}
                        ${vehicle.fuel_type ? `<div><i class="fas fa-gas-pump mr-1"></i>${vehicle.fuel_type}</div>` : ''}
                    </div>
                    ${vehicle.location ? `<div class="mt-2 text-sm text-gray-600"><i class="fas fa-map-marker-alt mr-1"></i>${vehicle.location}</div>` : ''}
                </div>
                <div class="text-right ml-4">
                    <div class="text-xl font-bold text-gray-900 mb-2">${vehicle.price}</div>
                    <div class="flex items-center space-x-2">
                        <span class="status-${vehicle.status} text-sm font-medium">
                            <i class="fas fa-circle text-xs mr-1"></i>
                            ${getStatusText(vehicle.status)}
                        </span>
                        <a href="${vehicle.url}" target="_blank" class="text-blue-600 hover:text-blue-800">
                            <i class="fas fa-external-link-alt"></i>
                        </a>
                    </div>
                    <div class="text-xs text-gray-500 mt-1">
                        Visto: ${formatDate(vehicle.last_seen)}
                    </div>
                </div>
            </div>
        </div>
    `).join('');
}

// Render pagination
function renderPagination(currentPage, totalPages) {
    const container = document.getElementById('pagination');

    if (totalPages <= 1) {
        container.innerHTML = '';
        return;
    }

    let pagination = '<div class="flex space-x-2">';

    // Previous button
    if (currentPage > 1) {
        pagination += `<button onclick="changePage(${currentPage - 1})" class="px-3 py-2 border border-gray-300 rounded-lg hover:bg-gray-50">Anterior</button>`;
    }

    // Page numbers
    for (let i = Math.max(1, currentPage - 2); i <= Math.min(totalPages, currentPage + 2); i++) {
        const isActive = i === currentPage;
        pagination += `<button onclick="changePage(${i})" class="px-3 py-2 border ${isActive ? 'bg-blue-600 text-white border-blue-600' : 'border-gray-300 hover:bg-gray-50'} rounded-lg">${i}</button>`;
    }

    // Next button
    if (currentPage < totalPages) {
        pagination += `<button onclick="changePage(${currentPage + 1})" class="px-3 py-2 border border-gray-300 rounded-lg hover:bg-gray-50">Próximo</button>`;
    }

    pagination += '</div>';
    container.innerHTML = pagination;
}

// Change page
function changePage(page) {
    currentPage = page;
    loadVehicles();
}

// Run scraping
async function runScraping() {
    const result = await apiCall('/scraper/run', { method: 'POST' });
    if (result) {
        showSuccess('Scraping iniciado com sucesso!');
        checkScrapingStatus();
    }
}

// Check scraping status
async function checkScrapingStatus() {
    const status = await apiCall('/scraper/status');
    if (status) {
        if (status.is_running) {
            scrapingStatus.innerHTML = '<i class="fas fa-spinner loading mr-1"></i>Executando...';
            runScrapingBtn.disabled = true;
            runScrapingBtn.classList.add('opacity-50', 'cursor-not-allowed');
        } else {
            scrapingStatus.innerHTML = status.last_run ? 
                `Última execução: ${formatDate(status.last_run)}` : 
                'Nunca executado';
            runScrapingBtn.disabled = false;
            runScrapingBtn.classList.remove('opacity-50', 'cursor-not-allowed');
        }
    }
}

// Utility functions
function getStatusText(status) {
    const statusMap = {
        'active': 'Ativo',
        'sold': 'Vendido',
        'removed': 'Removido'
    };
    return statusMap[status] || status;
}

function formatDate(dateString) {
    if (!dateString) return 'N/A';
    const date = new Date(dateString);
    return date.toLocaleString('pt-BR');
}

function showLoading() {
    loadingModal.classList.remove('hidden');
    loadingModal.classList.add('flex');
}

function hideLoading() {
    loadingModal.classList.add('hidden');
    loadingModal.classList.remove('flex');
}

function showSuccess(message) {
    // Simple alert for now - could be replaced with a toast notification
    alert(message);
}

function showError(message) {
    // Simple alert for now - could be replaced with a toast notification
    alert(message);
}