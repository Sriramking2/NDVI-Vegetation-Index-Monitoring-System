
let allHistoryData = [];
let filteredHistoryData = [];
let currentFilter = 'all';
let currentSearch = '';

// Initialize
(function initializeNow() {
    if (document.readyState === 'interactive' || document.readyState === 'complete') {
        setTimeout(startApp, 0);
    } else {
        document.addEventListener('DOMContentLoaded', startApp, { once: true });
    }
    
    addHealthLandscapeCSS();
})();

function startApp() {
    setupEventListeners();
    loadHistory();
}

// Add CSS for landscape health metrics display
function addHealthLandscapeCSS() {
    if (document.getElementById('health-landscape-css')) return;
    
    const style = document.createElement('style');
    style.id = 'health-landscape-css';
    style.textContent = `
        /* Health Metrics Styling - Landscape Layout */
        .health-score {
            padding: 2px 12px;
            border-radius: 20px;
            font-weight: 600;
            font-size: 12px;
            display: inline-block;
            margin-left: 5px;
        }
        
        .score-excellent { background: linear-gradient(135deg, #4CAF50 0%, #2E7D32 100%); color: white; }
        .score-good { background: linear-gradient(135deg, #8BC34A 0%, #689F38 100%); color: white; }
        .score-fair { background: linear-gradient(135deg, #FFC107 0%, #FF9800 100%); color: #333; }
        .score-poor { background: linear-gradient(135deg, #FF9800 0%, #F57C00 100%); color: white; }
        .score-critical { background: linear-gradient(135deg, #F44336 0%, #D32F2F 100%); color: white; }
        
        /* Health Badges */
        .health-badges {
            display: flex;
            gap: 8px;
            margin: 10px 0;
            flex-wrap: wrap;
        }
        
        .health-badge {
            padding: 4px 10px;
            border-radius: 12px;
            font-size: 11px;
            font-weight: 500;
            display: flex;
            align-items: center;
            gap: 5px;
        }
        
        .badge-soil {
            background: linear-gradient(135deg, #8B4513 0%, #A0522D 100%);
            color: white;
            border: none;
        }
        
        .badge-crop {
            background: linear-gradient(135deg, #2E7D32 0%, #4CAF50 100%);
            color: white;
            border: none;
        }
        
        /* Horizontal Card Layout */
        .history-card {
            background: white;
            border-radius: 12px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.08);
            overflow: hidden;
            transition: all 0.3s ease;
            margin-bottom: 20px;
            border: 1px solid #e0e0e0;
        }
        
        .history-card:hover {
            transform: translateY(-4px);
            box-shadow: 0 8px 24px rgba(0,0,0,0.12);
        }
        
        .card-header {
            padding: 16px 20px;
            background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
            border-bottom: 1px solid #dee2e6;
            display: flex;
            justify-content: space-between;
            align-items: center;
            flex-wrap: wrap;
        }
        
        .location-name {
            flex: 1;
            min-width: 200px;
        }
        
        .location-name h3 {
            margin: 0;
            color: #333;
            font-size: 18px;
            display: flex;
            align-items: center;
            gap: 8px;
        }
        
        .location-name h3 i {
            color: #4CAF50;
        }
        
        .date-time {
            color: #666;
            font-size: 14px;
            display: flex;
            align-items: center;
            gap: 6px;
            background: white;
            padding: 6px 12px;
            border-radius: 6px;
            border: 1px solid #dee2e6;
        }
        
        .date-time i {
            color: #2196F3;
        }
        
        /* Horizontal Card Body */
        .card-body {
            padding: 20px;
            display: flex;
            gap: 20px;
            flex-wrap: wrap;
        }
        
        /* Left Column - Images */
        .images-section {
            flex: 1;
            min-width: 300px;
        }
        
        .images-section h4 {
            margin: 0 0 12px 0;
            color: #333;
            font-size: 16px;
            display: flex;
            align-items: center;
            gap: 8px;
        }
        
        .images-section h4 i {
            color: #2196F3;
        }
        
        /* Horizontal Images Grid */
        .images-grid {
            display: flex;
            gap: 8px;
            overflow-x: auto;
            padding-bottom: 10px;
            scrollbar-width: thin;
        }
        
        .images-grid::-webkit-scrollbar {
            height: 6px;
        }
        
        .images-grid::-webkit-scrollbar-track {
            background: #f1f1f1;
            border-radius: 3px;
        }
        
        .images-grid::-webkit-scrollbar-thumb {
            background: #c1c1c1;
            border-radius: 3px;
        }
        
        .images-grid::-webkit-scrollbar-thumb:hover {
            background: #a8a8a8;
        }
        
        .image-container {
            min-width: 120px;
            height: 100px;
            border-radius: 8px;
            overflow: hidden;
            position: relative;
            background: #f5f5f5;
            flex-shrink: 0;
            transition: all 0.3s ease;
        }
        
        .image-container:hover {
            transform: translateY(-3px);
            box-shadow: 0 6px 12px rgba(0,0,0,0.15);
        }
        
        .image-container img {
            width: 100%;
            height: 100%;
            object-fit: cover;
            border-radius: 8px;
        }
        
        .image-label {
            position: absolute;
            bottom: 0;
            left: 0;
            right: 0;
            background: rgba(0, 0, 0, 0.7);
            color: white;
            font-size: 10px;
            font-weight: 500;
            text-align: center;
            padding: 4px;
            border-radius: 0 0 8px 8px;
        }
        
        .image-placeholder {
            width: 100%;
            height: 100%;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            color: #999;
            font-size: 11px;
        }
        
        .image-placeholder i {
            font-size: 24px;
            margin-bottom: 8px;
            color: #ccc;
        }
        
        /* Right Column - Health Metrics */
        .health-section {
            flex: 1;
            min-width: 300px;
        }
        
        .health-section h4 {
            margin: 0 0 12px 0;
            color: #333;
            font-size: 16px;
            display: flex;
            align-items: center;
            gap: 8px;
        }
        
        .health-section h4 i {
            color: #4CAF50;
        }
        
        /* Single Horizontal Health Container */
        .single-health-container {
            display: flex;
            gap: 15px;
            flex-wrap: wrap;
        }
        
        .health-card {
            flex: 1;
            min-width: 200px;
            padding: 15px;
            border-radius: 10px;
            border: 1px solid #dee2e6;
            transition: all 0.3s ease;
        }
        
        .health-card:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(0,0,0,0.1);
        }
        
        .health-card.soil {
            border-left: 4px solid #8B4513;
            background: linear-gradient(135deg, #FFF3E0 0%, #FFECB3 100%);
        }
        
        .health-card.crop {
            border-left: 4px solid #2E7D32;
            background: linear-gradient(135deg, #E8F5E9 0%, #C8E6C9 100%);
        }
        
        .health-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 15px;
        }
        
        .health-title {
            display: flex;
            align-items: center;
            gap: 8px;
            font-weight: 600;
            color: #333;
            font-size: 15px;
        }
        
        .health-title i {
            font-size: 18px;
        }
        
        .health-score-large {
            font-size: 24px;
            font-weight: 700;
            color: white;
            padding: 8px 16px;
            border-radius: 8px;
            min-width: 80px;
            text-align: center;
        }
        
        .soil .health-score-large {
            background: linear-gradient(135deg, #8B4513 0%, #A0522D 100%);
        }
        
        .crop .health-score-large {
            background: linear-gradient(135deg, #2E7D32 0%, #4CAF50 100%);
        }
        
        .health-metrics-horizontal {
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 10px;
        }
        
        .health-metric-horizontal {
            background: white;
            padding: 10px;
            border-radius: 8px;
            border: 1px solid #eee;
            transition: all 0.2s;
        }
        
        .health-metric-horizontal:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 8px rgba(0,0,0,0.1);
        }
        
        .metric-label-horizontal {
            font-size: 11px;
            color: #666;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            margin-bottom: 4px;
        }
        
        .metric-value-horizontal {
            font-size: 16px;
            font-weight: 600;
            margin-bottom: 6px;
        }
        
        .soil .metric-value-horizontal {
            color: #8B4513;
        }
        
        .crop .metric-value-horizontal {
            color: #2E7D32;
        }
        
        /* Progress Bars */
        .metric-progress-horizontal {
            height: 6px;
            background: rgba(0,0,0,0.1);
            border-radius: 3px;
            margin-top: 5px;
            overflow: hidden;
        }
        
        .progress-fill-horizontal {
            height: 100%;
            border-radius: 3px;
        }
        
        .soil .progress-fill-horizontal {
            background: linear-gradient(90deg, #8B4513 0%, #A0522D 100%);
        }
        
        .crop .progress-fill-horizontal {
            background: linear-gradient(90deg, #2E7D32 0%, #4CAF50 100%);
        }
        
        /* Card Actions - Bottom Row */
        .card-actions-row {
            display: flex;
            gap: 10px;
            margin-top: 20px;
            padding-top: 20px;
            border-top: 1px solid #eee;
            flex-wrap: wrap;
        }
        
        /* Action Buttons */
        .action-btn {
            padding: 10px 16px;
            border-radius: 6px;
            font-size: 14px;
            font-weight: 500;
            cursor: pointer;
            border: none;
            display: flex;
            align-items: center;
            gap: 8px;
            transition: all 0.2s;
        }
        
        .action-btn.view {
            background: #2196F3;
            color: white;
        }
        
        .action-btn.download {
            background: #FF9800;
            color: white;
        }
        
        .action-btn.delete {
            background: #F44336;
            color: white;
        }
        
        .action-btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(0,0,0,0.2);
        }
        
        /* Filter button active state */
        .filter-btn.active {
            background: linear-gradient(135deg, #4CAF50 0%, #2E7D32 100%) !important;
            color: white !important;
            transform: translateY(-2px);
            box-shadow: 0 4px 8px rgba(76, 175, 80, 0.3);
        }
        
        /* Smooth transitions */
        #historyGrid, #statsContainer, #emptyState, #loadingState {
            transition: opacity 0.3s ease, transform 0.3s ease;
        }
        
        /* Responsive adjustments */
        @media (max-width: 768px) {
            .card-body {
                flex-direction: column;
            }
            
            .images-section,
            .health-section {
                min-width: 100%;
            }
            
            .single-health-container {
                flex-direction: column;
            }
            
            .health-card {
                min-width: 100%;
            }
            
            .health-metrics-horizontal {
                grid-template-columns: repeat(2, 1fr);
            }
            
            .card-header {
                flex-direction: column;
                align-items: flex-start;
                gap: 10px;
            }
            
            .date-time {
                align-self: flex-start;
            }
            
            .image-container {
                min-width: 100px;
                height: 90px;
            }
            
            .image-placeholder {
                font-size: 10px;
            }
            
            .image-placeholder i {
                font-size: 20px;
            }
        }
        
        /* No health data message */
        .no-health-data {
            text-align: center;
            padding: 20px;
            background: #f8f9fa;
            border-radius: 8px;
            color: #666;
            font-size: 14px;
        }
        
        .no-health-data i {
            font-size: 24px;
            margin-bottom: 10px;
            color: #ccc;
        }
    `;
    document.head.appendChild(style);
    
    setTimeout(() => {
        document.body.classList.add('loaded');
    }, 100);
}

// Load history with health data
async function loadHistory() {
    try {
        showLoading();
        
        await new Promise(resolve => setTimeout(resolve, 50));
        
        const response = await fetch('/get_history_data');
        if (!response.ok) {
            throw new Error('Failed to load history');
        }
        
        const data = await response.json();
        allHistoryData = data.history || [];
        
        // Load health data for each analysis
        await loadHealthData();
        
        updateStats();
        
        setTimeout(() => {
            filterHistory('all');
            hideLoading();
        }, 100);
        
    } catch (error) {
        console.error('Error loading history:', error);
        showEmptyState('Failed to load history data. Please try again.');
        hideLoading();
    }
}

// Load health data for each analysis
async function loadHealthData() {
    for (let i = 0; i < allHistoryData.length; i++) {
        const item = allHistoryData[i];
        if (item.id) {
            try {
                const response = await fetch(`/get_detailed_health_metrics?id=${item.id}`);
                if (response.ok) {
                    const healthData = await response.json();
                    if (healthData.success) {
                        // Merge health data
                        allHistoryData[i].soil_metrics = healthData.soil_metrics || {};
                        allHistoryData[i].crop_metrics = healthData.crop_metrics || {};
                        allHistoryData[i].recommendations = healthData.recommendations || [];
                        allHistoryData[i].has_health_data = true;
                        
                        // Store health scores
                        allHistoryData[i].soil_health_score = healthData.soil_metrics?.health_score || 0;
                        allHistoryData[i].crop_health_score = healthData.crop_metrics?.health_score || 0;
                        
                        // Add PNG file names if available
                        if (healthData.file_status) {
                            allHistoryData[i].soil_health_png = healthData.file_status.soil_health_png?.exists ? 
                                healthData.file_status.soil_health_png.url?.replace('/static/ndvi/', '') : null;
                            allHistoryData[i].crop_health_png = healthData.file_status.crop_health_png?.exists ? 
                                healthData.file_status.crop_health_png.url?.replace('/static/ndvi/', '') : null;
                        }
                    }
                }
            } catch (error) {
                console.error(`Error loading health data for analysis ${item.id}:`, error);
                allHistoryData[i].has_health_data = false;
            }
        }
    }
}

// Update statistics with health info
function updateStats() {
    const statsContainer = document.getElementById('statsContainer');
    
    const totalAnalyses = allHistoryData.length;
    const today = new Date().toISOString().split('T')[0];
    const recentAnalyses = allHistoryData.filter(item => 
        item.datetime && item.datetime.includes(today)
    ).length;
    
    const uniqueLocations = [...new Set(allHistoryData.map(item => item.place_name))].length;
    
    // Health statistics - show separate soil and crop scores
    const analysesWithSoil = allHistoryData.filter(item => item.soil_health_score);
    const avgSoilScore = analysesWithSoil.length > 0 ? 
        analysesWithSoil.reduce((sum, item) => sum + (item.soil_health_score || 0), 0) / analysesWithSoil.length : 0;
    
    statsContainer.innerHTML = `
        <div class="stat-card" style="opacity: 0; transform: translateY(20px);">
            <div class="stat-icon total">
                <i class="fas fa-chart-bar"></i>
            </div>
            <div class="stat-content">
                <h3>${totalAnalyses}</h3>
                <p>Total Analyses</p>
            </div>
        </div>
        <div class="stat-card" style="opacity: 0; transform: translateY(20px);">
            <div class="stat-icon recent">
                <i class="fas fa-clock"></i>
            </div>
            <div class="stat-content">
                <h3>${recentAnalyses}</h3>
                <p>Today's Analyses</p>
            </div>
        </div>
        <div class="stat-card" style="opacity: 0; transform: translateY(20px);">
            <div class="stat-icon locations">
                <i class="fas fa-map-marker-alt"></i>
            </div>
            <div class="stat-content">
                <h3>${uniqueLocations}</h3>
                <p>Locations</p>
            </div>
        </div>

    `;
    
    // Animate stats in
    setTimeout(() => {
        document.querySelectorAll('.stat-card').forEach((card, i) => {
            setTimeout(() => {
                card.style.opacity = '1';
                card.style.transform = 'translateY(0)';
            }, i * 100);
        });
    }, 100);
}

// Filter history
function filterHistory(filterType, event = null) {
    currentFilter = filterType;
    
    // Update all filter buttons
    document.querySelectorAll('.filter-btn').forEach(btn => {
        btn.classList.remove('active');
    });
    
    // Activate the clicked button
    if (event) {
        event.target.classList.add('active');
    } else {
        // If called without event, find the matching button
        const filterButtons = document.querySelectorAll('.filter-btn');
        filterButtons.forEach(btn => {
            if (btn.textContent.trim().toLowerCase() === filterType.toLowerCase()) {
                btn.classList.add('active');
            }
        });
    }
    
    // Apply filter
    const now = new Date();
    filteredHistoryData = allHistoryData.filter(item => {
        if (!item.datetime) return false;
        
        const itemDate = new Date(item.datetime.replace(' ', 'T'));
        
        switch(filterType) {
            case 'today':
                return itemDate.toDateString() === now.toDateString();
            case 'week':
                const oneWeekAgo = new Date(now.getTime() - 7 * 24 * 60 * 60 * 1000);
                return itemDate >= oneWeekAgo;
            case 'month':
                const oneMonthAgo = new Date(now.getTime() - 30 * 24 * 60 * 60 * 1000);
                return itemDate >= oneMonthAgo;
            default:
                return true;
        }
    });
    
    // Apply search
    if (currentSearch) {
        filteredHistoryData = filteredHistoryData.filter(item => 
            item.place_name && item.place_name.toLowerCase().includes(currentSearch.toLowerCase())
        );
    }
    
    displayHistory();
}

// Display history with horizontal layout
function displayHistory() {
    const historyGrid = document.getElementById('historyGrid');
    const emptyState = document.getElementById('emptyState');
    
    if (filteredHistoryData.length === 0) {
        historyGrid.style.display = 'none';
        emptyState.style.display = 'block';
        return;
    }
    
    // Sort by date (newest first)
    const sortedData = [...filteredHistoryData].sort((a, b) => {
        return new Date(b.datetime || b.timestamp || 0) - new Date(a.datetime || a.timestamp || 0);
    });
    
    historyGrid.innerHTML = sortedData.map((item, index) => {
        const soilScore = item.soil_health_score || 0;
        const cropScore = item.crop_health_score || 0;
        const soilScoreClass = getHealthScoreClass(soilScore);
        const cropScoreClass = getHealthScoreClass(cropScore);
        
        return `
            <div class="history-card">
                <div class="card-header">
                    <div class="location-name">
                        <h3><i class="fas fa-map-marker-alt"></i> ${item.place_name || 'Unknown Location'}</h3>
                    </div>
                    <div class="date-time">
                        <i class="far fa-clock"></i> ${formatDateTime(item.datetime || item.timestamp || '')}
                    </div>
                </div>
                
                <div class="card-body">
                    <!-- Left Column: Images -->
                    <div class="images-section">
                        <h4><i class="fas fa-images"></i> Analysis Images</h4>
                        <div class="images-grid">
                            ${createImageGrid(item)}
                        </div>
                    </div>
                    
                    <!-- Right Column: Health Metrics -->
                    <div class="health-section">
                        <h4><i class="fas fa-heartbeat"></i> Health Metrics</h4>
                        ${item.has_health_data ? renderHorizontalHealthMetrics(item) : renderNoHealthData()}
                    </div>
                </div>
                
                <!-- Actions Row -->
                <div class="card-actions-row">
                    <button class="action-btn view" onclick="viewAnalysis(${index})">
                        <i class="fas fa-eye"></i> View Details
                    </button>
                    <button class="action-btn download" onclick="downloadAnalysis(${index})">
                        <i class="fas fa-download"></i> Download
                    </button>
                    <button class="action-btn delete" onclick="deleteAnalysis(${index})">
                        <i class="fas fa-trash"></i> Delete
                    </button>
                </div>
            </div>
        `;
    }).join('');
    
    historyGrid.style.display = 'grid';
    emptyState.style.display = 'none';
}

// Render horizontal health metrics (side by side cards)
function renderHorizontalHealthMetrics(item) {
    if (!item.soil_metrics && !item.crop_metrics) return renderNoHealthData();
    
    const soilScore = item.soil_metrics?.health_score || 0;
    const cropScore = item.crop_metrics?.health_score || 0;
    
    return `
        <div class="single-health-container">
            <!-- Soil Health Card -->
            <div class="health-card soil">
                <div class="health-header">
                    <div class="health-title">
                        <i class="fas fa-mountain"></i>
                        <span>Soil Health</span>
                    </div>
                    <div class="health-score-large">
                        ${soilScore.toFixed(1)}%
                    </div>
                </div>
                <div class="health-metrics-horizontal">
                    ${renderSoilMetricsHorizontal(item.soil_metrics)}
                </div>
            </div>
            
            <!-- Crop Health Card -->
            <div class="health-card crop">
                <div class="health-header">
                    <div class="health-title">
                        <i class="fas fa-leaf"></i>
                        <span>Crop Health</span>
                    </div>
                    <div class="health-score-large">
                        ${cropScore.toFixed(1)}%
                    </div>
                </div>
                <div class="health-metrics-horizontal">
                    ${renderCropMetricsHorizontal(item.crop_metrics)}
                </div>
            </div>
        </div>
    `;
}

// Render soil metrics horizontally
function renderSoilMetricsHorizontal(metrics) {
    if (!metrics) return '';
    
    return `
        <div class="health-metric-horizontal">
            <div class="metric-label-horizontal">Moisture</div>
            <div class="metric-value-horizontal">${metrics.moisture_index || 0}%</div>
            <div class="metric-progress-horizontal">
                <div class="progress-fill-horizontal" style="width: ${metrics.moisture_index || 0}%"></div>
            </div>
        </div>
        <div class="health-metric-horizontal">
            <div class="metric-label-horizontal">Organic Matter</div>
            <div class="metric-value-horizontal">${metrics.organic_matter || 0}%</div>
            <div class="metric-progress-horizontal">
                <div class="progress-fill-horizontal" style="width: ${metrics.organic_matter || 0}%"></div>
            </div>
        </div>
        <div class="health-metric-horizontal">
            <div class="metric-label-horizontal">Texture</div>
            <div class="metric-value-horizontal">${metrics.texture_score || 0}%</div>
            <div class="metric-progress-horizontal">
                <div class="progress-fill-horizontal" style="width: ${metrics.texture_score || 0}%"></div>
            </div>
        </div>
        <div class="health-metric-horizontal">
            <div class="metric-label-horizontal">pH Level</div>
            <div class="metric-value-horizontal">${metrics.ph_level || 0}</div>
            <div class="metric-progress-horizontal">
                <div class="progress-fill-horizontal" style="width: ${Math.min((metrics.ph_level || 0) * 10, 100)}%"></div>
            </div>
        </div>
    `;
}

// Render crop metrics horizontally
function renderCropMetricsHorizontal(metrics) {
    if (!metrics) return '';
    
    return `
        <div class="health-metric-horizontal">
            <div class="metric-label-horizontal">Vigor</div>
            <div class="metric-value-horizontal">${metrics.vigor_index || 0}%</div>
            <div class="metric-progress-horizontal">
                <div class="progress-fill-horizontal" style="width: ${metrics.vigor_index || 0}%"></div>
            </div>
        </div>
        <div class="health-metric-horizontal">
            <div class="metric-label-horizontal">Chlorophyll</div>
            <div class="metric-value-horizontal">${metrics.chlorophyll_content || 0}%</div>
            <div class="metric-progress-horizontal">
                <div class="progress-fill-horizontal" style="width: ${metrics.chlorophyll_content || 0}%"></div>
            </div>
        </div>
        <div class="health-metric-horizontal">
            <div class="metric-label-horizontal">Stress Level</div>
            <div class="metric-value-horizontal">${metrics.stress_level || 0}%</div>
            <div class="metric-progress-horizontal">
                <div class="progress-fill-horizontal" style="width: ${100 - (metrics.stress_level || 0)}%"></div>
            </div>
        </div>
        <div class="health-metric-horizontal">
            <div class="metric-label-horizontal">Yield Potential</div>
            <div class="metric-value-horizontal">${metrics.yield_potential || 0}%</div>
            <div class="metric-progress-horizontal">
                <div class="progress-fill-horizontal" style="width: ${metrics.yield_potential || 0}%"></div>
            </div>
        </div>
    `;
}

// Render no health data message
function renderNoHealthData() {
    return `
        <div class="no-health-data">
            <i class="fas fa-exclamation-circle"></i>
            <p>No health data available</p>
        </div>
    `;
}

// Get health score class
function getHealthScoreClass(score) {
    if (score >= 80) return 'score-excellent';
    if (score >= 65) return 'score-good';
    if (score >= 50) return 'score-fair';
    if (score >= 35) return 'score-poor';
    return 'score-critical';
}

// Search history with debounce
let searchTimeout;
function searchHistory() {
    clearTimeout(searchTimeout);
    
    const searchInput = document.getElementById('searchInput');
    currentSearch = searchInput.value.trim();
    
    searchTimeout = setTimeout(() => {
        filterHistory(currentFilter);
    }, 300);
}

// Clear search
function clearSearch() {
    const searchInput = document.getElementById('searchInput');
    searchInput.value = '';
    currentSearch = '';
    filterHistory(currentFilter);
}

// Create image grid for a history item
function createImageGrid(item) {
    const images = [
        { key: 'ndvi_png', label: 'NDVI', icon: 'fas fa-leaf', color: '#2E7D32' },
        { key: 'rgb_png', label: 'RGB', icon: 'fas fa-image', color: '#2196F3' },
        { key: 'savi_png', label: 'SAVI', icon: 'fas fa-tree', color: '#8B4513' },
        { key: 'gndvi_png', label: 'GNDVI', icon: 'fas fa-seedling', color: '#4CAF50' },
        { key: 'evi_png', label: 'EVI', icon: 'fas fa-chart-line', color: '#FF9800' },
        { key: 'soil_health_png', label: 'Soil Health', icon: 'fas fa-mountain', color: '#8B4513' },
        { key: 'crop_health_png', label: 'Crop Health', icon: 'fas fa-leaf', color: '#228B22' }
    ];
    
    return images.map(img => {
        const hasImage = item[img.key];
        const imageUrl = hasImage ? `/static/ndvi/${item[img.key]}` : '';
        
        return `
            <div class="image-container" ${hasImage ? `onclick="viewImage('${imageUrl}', '${img.label}')" style="cursor: pointer;"` : ''}>
                ${hasImage ? 
                    `<img src="${imageUrl}" alt="${img.label}" loading="lazy">
                     <div class="image-label">${img.label}</div>` :
                    `<div class="image-placeholder" style="background: linear-gradient(135deg, ${img.color}15 0%, ${img.color}25 100%);">
                        <i class="${img.icon}" style="color: ${img.color}80;"></i>
                        <span>No ${img.label}</span>
                    </div>`
                }
            </div>
        `;
    }).join('');
}


// Format date time
function formatDateTime(dateTimeStr) {
    if (!dateTimeStr) return 'Unknown date';
    
    try {
        const date = new Date(dateTimeStr.replace(' ', 'T'));
        return date.toLocaleDateString() + ' ' + date.toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'});
    } catch {
        return dateTimeStr;
    }
}

// Setup event listeners
function setupEventListeners() {
    const searchInput = document.getElementById('searchInput');
    if (searchInput) {
        searchInput.addEventListener('input', searchHistory);
    }
    
    document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape') {
            closeModal();
        }
    });
    
    const modal = document.getElementById('imageModal');
    if (modal) {
        modal.addEventListener('click', function(e) {
            if (e.target === this) {
                closeModal();
            }
        });
    }
    
    const clearBtn = document.querySelector('[onclick="clearSearch()"]');
    if (clearBtn) {
        clearBtn.addEventListener('click', clearSearch);
    }
    
    // Add click listeners to filter buttons
    document.querySelectorAll('.filter-btn').forEach(btn => {
        btn.addEventListener('click', function(e) {
            const filterType = this.textContent.trim().toLowerCase();
            filterHistory(filterType, e);
        });
    });
}

// View image in modal
function viewImage(imageUrl, title) {
    const modal = document.getElementById('imageModal');
    const modalImage = document.getElementById('modalImage');
    const modalTitle = document.getElementById('modalTitle');
    
    // Create image element
    modalImage.innerHTML = `<img src="${imageUrl}" alt="${title}" style="max-width: 100%; max-height: 70vh; border-radius: 8px;">`;
    modalTitle.textContent = title + ' Preview';
    modal.style.display = 'flex';
    
    // Fade in modal
    setTimeout(() => {
        modal.style.opacity = '1';
    }, 10);
}

// View analysis details
function viewAnalysis(index) {
    const item = filteredHistoryData[index];
    
    let details = `Analysis Details:\n\n`;
    details += `Location: ${item.place_name || 'N/A'}\n`;
    details += `Date: ${item.datetime || item.timestamp || 'N/A'}\n`;
    details += `Soil Health: ${item.soil_health_score ? item.soil_health_score.toFixed(1) + '%' : 'N/A'}\n`;
    details += `Crop Health: ${item.crop_health_score ? item.crop_health_score.toFixed(1) + '%' : 'N/A'}\n\n`;
    
    details += `Images Generated:\n`;
    details += `• NDVI: ${item.ndvi_png ? '✓' : '✗'}\n`;
    details += `• RGB: ${item.rgb_png ? '✓' : '✗'}\n`;
    details += `• SAVI: ${item.savi_png ? '✓' : '✗'}\n`;
    details += `• GNDVI: ${item.gndvi_png ? '✓' : '✗'}\n`;
    details += `• EVI: ${item.evi_png ? '✓' : '✗'}\n`;
    details += `• Soil Health Map: ${item.soil_health_png ? '✓' : '✗'}\n`;
    details += `• Crop Health Map: ${item.crop_health_png ? '✓' : '✗'}\n`;
    details += `• GeoTIFF: ${item.ndvi_tif ? '✓' : '✗'}\n\n`;
    
    if (item.soil_metrics) {
        details += `Soil Metrics:\n`;
        details += `• Health Score: ${item.soil_metrics.health_score || 0}%\n`;
        details += `• Moisture: ${item.soil_metrics.moisture_index || 0}%\n`;
        details += `• Organic Matter: ${item.soil_metrics.organic_matter || 0}%\n`;
        details += `• Texture: ${item.soil_metrics.texture_score || 0}%\n`;
        details += `• pH Level: ${item.soil_metrics.ph_level || 0}\n`;
    }
    
    if (item.crop_metrics) {
        details += `\nCrop Metrics:\n`;
        details += `• Health Score: ${item.crop_metrics.health_score || 0}%\n`;
        details += `• Vigor: ${item.crop_metrics.vigor_index || 0}%\n`;
        details += `• Chlorophyll: ${item.crop_metrics.chlorophyll_content || 0}%\n`;
        details += `• Stress Level: ${item.crop_metrics.stress_level || 0}%\n`;
        details += `• Yield Potential: ${item.crop_metrics.yield_potential || 0}%\n`;
    }
    
    alert(details);
}

// Download analysis
async function downloadAnalysis(index) {
    const item = filteredHistoryData[index];
    
    try {
        const zip = new JSZip();
        const folder = zip.folder(`ndvi_analysis_${item.place_name || 'analysis'}`);
        
        // Add README with health data
        const readme = `NDVI Analysis Export\n` +
                      `===================\n` +
                      `Location: ${item.place_name || 'Unknown'}\n` +
                      `Date: ${item.datetime || item.timestamp || 'Unknown'}\n` +
                      `Soil Health Score: ${item.soil_health_score ? item.soil_health_score.toFixed(1) + '%' : 'N/A'}\n` +
                      `Crop Health Score: ${item.crop_health_score ? item.crop_health_score.toFixed(1) + '%' : 'N/A'}\n\n` +
                      `Soil Health Metrics:\n` +
                      `• Health Score: ${item.soil_metrics?.health_score || 0}%\n` +
                      `• Moisture Index: ${item.soil_metrics?.moisture_index || 0}%\n` +
                      `• Organic Matter: ${item.soil_metrics?.organic_matter || 0}%\n` +
                      `• Texture Score: ${item.soil_metrics?.texture_score || 0}%\n` +
                      `• pH Level: ${item.soil_metrics?.ph_level || 0}\n\n` +
                      `Crop Health Metrics:\n` +
                      `• Health Score: ${item.crop_metrics?.health_score || 0}%\n` +
                      `• Vigor Index: ${item.crop_metrics?.vigor_index || 0}%\n` +
                      `• Chlorophyll Content: ${item.crop_metrics?.chlorophyll_content || 0}%\n` +
                      `• Stress Level: ${item.crop_metrics?.stress_level || 0}%\n` +
                      `• Yield Potential: ${item.crop_metrics?.yield_potential || 0}%\n\n` +
                      `Files included in this export:`;
        
        folder.file('README.txt', readme);
        
        // Add images - INCLUDING SOIL AND CROP HEALTH PNGs
        const images = [
            { key: 'ndvi_png', name: 'NDVI.png' },
            { key: 'rgb_png', name: 'RGB.png' },
            { key: 'savi_png', name: 'SAVI.png' },
            { key: 'gndvi_png', name: 'GNDVI.png' },
            { key: 'evi_png', name: 'EVI.png' },
            { key: 'soil_health_png', name: 'Soil_Health.png' },
            { key: 'crop_health_png', name: 'Crop_Health.png' },
            { key: 'ndvi_tif', name: 'NDVI_GeoTIFF.tif' }
        ];
        
        let addedCount = 0;
        
        for (const img of images) {
            if (item[img.key]) {
                try {
                    const response = await fetch(`/static/ndvi/${item[img.key]}`);
                    if (response.ok) {
                        const blob = await response.blob();
                        folder.file(img.name, blob);
                        addedCount++;
                        console.log(`Added ${img.name} to ZIP`);
                    }
                } catch (error) {
                    console.error(`Error downloading ${img.key}:`, error);
                }
            } else {
                console.log(`No ${img.key} available for ${item.place_name}`);
            }
        }
        
        if (addedCount > 0) {
            const zipBlob = await zip.generateAsync({type: "blob"});
            const filename = `ndvi_analysis_${item.place_name || 'analysis'}_${Date.now()}.zip`;
            
            saveAs(zipBlob, filename);
            
            // Show download confirmation
            showMessage(`Download started! ${addedCount} file(s) included in ZIP.`, 'success');
        } else {
            showMessage('No files available for download.', 'warning');
        }
        
    } catch (error) {
        console.error('Error creating ZIP:', error);
        showMessage('Error creating download. Please try again.', 'error');
    }
}

// Delete analysis
async function deleteAnalysis(index) {
    const item = filteredHistoryData[index];
    
    if (!confirm(`Delete analysis for "${item.place_name || 'this location'}"? This action cannot be undone.`)) {
        return;
    }
    
    try {
        const response = await fetch('/delete_history', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ id: item.id })
        });
        
        if (response.ok) {
            // Remove from local arrays
            const itemId = item.id;
            allHistoryData = allHistoryData.filter(h => h.id !== itemId);
            filteredHistoryData = filteredHistoryData.filter(h => h.id !== itemId);
            
            // Update display
            updateStats();
            displayHistory();
            
            alert('Analysis deleted successfully!');
        } else {
            throw new Error('Delete failed');
        }
        
    } catch (error) {
        console.error('Error deleting analysis:', error);
        alert('Failed to delete analysis. Please try again.');
    }
}

// Export all history
function exportHistory() {
    if (allHistoryData.length === 0) {
        alert('No history data to export.');
        return;
    }
    
    // Create CSV with health data
    const csvHeaders = [
        'Location', 'Date', 'Soil Health', 'Crop Health',
        'Soil Moisture', 'Soil Organic Matter', 'Soil Texture', 'Soil pH',
        'Crop Vigor', 'Crop Chlorophyll', 'Crop Stress', 'Crop Yield',
        'NDVI', 'RGB', 'SAVI', 'GNDVI', 'EVI', 'GeoTIFF'
    ];
    
    const csvRows = allHistoryData.map(item => [
        item.place_name || '',
        item.datetime || item.timestamp || '',
        item.soil_health_score || '',
        item.crop_health_score || '',
        item.soil_metrics?.moisture_index || '',
        item.soil_metrics?.organic_matter || '',
        item.soil_metrics?.texture_score || '',
        item.soil_metrics?.ph_level || '',
        item.crop_metrics?.vigor_index || '',
        item.crop_metrics?.chlorophyll_content || '',
        item.crop_metrics?.stress_level || '',
        item.crop_metrics?.yield_potential || '',
        item.ndvi_png ? 'Yes' : 'No',
        item.rgb_png ? 'Yes' : 'No',
        item.savi_png ? 'Yes' : 'No',
        item.gndvi_png ? 'Yes' : 'No',
        item.evi_png ? 'Yes' : 'No',
        item.ndvi_tif ? 'Yes' : 'No'
    ]);
    
    const csvContent = [
        csvHeaders.join(','),
        ...csvRows.map(row => row.map(cell => `"${cell}"`).join(','))
    ].join('\n');
    
    // Create download link
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const url = window.URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `ndvi_history_${new Date().toISOString().split('T')[0]}.csv`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    
    alert(`Exported ${allHistoryData.length} records to CSV.`);
}

// Clear all history
function clearAllHistory() {
    if (allHistoryData.length === 0) {
        alert('No history to clear.');
        return;
    }
    
    if (!confirm(`Are you sure you want to delete ALL ${allHistoryData.length} analyses? This action cannot be undone.`)) {
        return;
    }
    
    // In a real app, you would make an API call to delete from server
    // For now, we'll just clear the local display
    allHistoryData = [];
    filteredHistoryData = [];
    updateStats();
    displayHistory();
    
    alert('All history cleared from display. Note: Files may still exist on server.');
}

// Show loading state
function showLoading() {
    const loading = document.getElementById('loadingState');
    if (loading) {
        loading.style.display = 'flex';
        loading.style.opacity = '0';
        setTimeout(() => {
            loading.style.opacity = '1';
        }, 10);
    }
}

// Hide loading
function hideLoading() {
    const loading = document.getElementById('loadingState');
    if (loading) {
        loading.style.opacity = '0';
        setTimeout(() => {
            loading.style.display = 'none';
        }, 300);
    }
}

// Show empty state
function showEmptyState(message) {
    const emptyState = document.getElementById('emptyState');
    if (emptyState) {
        emptyState.querySelector('h3').textContent = message;
        emptyState.style.display = 'block';
        emptyState.style.opacity = '0';
        emptyState.style.transform = 'translateY(10px)';
        
        document.getElementById('historyGrid').style.display = 'none';
        document.getElementById('loadingState').style.display = 'none';
        
        setTimeout(() => {
            emptyState.style.opacity = '1';
            emptyState.style.transform = 'translateY(0)';
        }, 10);
    }
}

// Close modal
function closeModal() {
    const modal = document.getElementById('imageModal');
    if (modal) {
        modal.style.opacity = '0';
        setTimeout(() => {
            modal.style.display = 'none';
            // Reset modal content
            modal.innerHTML = `
                <div class="modal-content">
                    <span class="close-modal" onclick="closeModal()">&times;</span>
                    <h2 id="modalTitle"></h2>
                    <div id="modalImage"></div>
                </div>
            `;
        }, 300);
    }
}

// Show help
function showHelp() {
    alert('History Page Help\n\n' +
          '1. View all your past NDVI analyses with health metrics\n' +
          '2. Filter by time period using the buttons\n' +
          '3. Search for specific locations\n' +
          '4. Click on images to view them larger\n' +
          '5. View details for each analysis\n' +
          '6. Download individual analyses or export all data\n' +
          '7. Delete analyses you no longer need\n\n' +
          'Health Metrics Display:\n' +
          '• Soil Health: Moisture, Organic Matter, Texture, pH\n' +
          '• Crop Health: Vigor, Chlorophyll, Stress, Yield Potential');
}

// Refresh history
function refreshHistory() {
    loadHistory();
}

// Optional: Auto-refresh
function startAutoRefresh() {
    // Refresh every 30 seconds if on the page
    setInterval(() => {
        if (document.visibilityState === 'visible') {
            loadHistory();
        }
    }, 30000);
}

// Get health insights summary
function getHealthInsights() {
    if (allHistoryData.length === 0) return;
    
    const analysesWithSoil = allHistoryData.filter(item => item.soil_health_score);
    const analysesWithCrop = allHistoryData.filter(item => item.crop_health_score);
    
    if (analysesWithSoil.length === 0 && analysesWithCrop.length === 0) return;
    
    const avgSoilScore = analysesWithSoil.length > 0 ? 
        analysesWithSoil.reduce((sum, item) => sum + (item.soil_health_score || 0), 0) / analysesWithSoil.length : 0;
    
    const avgCropScore = analysesWithCrop.length > 0 ? 
        analysesWithCrop.reduce((sum, item) => sum + (item.crop_health_score || 0), 0) / analysesWithCrop.length : 0;
    
    console.log('Health Insights:');
    console.log(`Average Soil Health: ${avgSoilScore.toFixed(1)}% (${analysesWithSoil.length} analyses)`);
    console.log(`Average Crop Health: ${avgCropScore.toFixed(1)}% (${analysesWithCrop.length} analyses)`);
    
    // You could display this in a modal or toast notification
    if (avgSoilScore < 50 || avgCropScore < 50) {
        showMessage('⚠️ Average health scores below optimal. Consider improvements.', 'warning');
    }
}

// Initialize health insights on load
setTimeout(getHealthInsights, 2000);

// Helper function to show messages
function showMessage(message, type = 'info') {
    // Create message element
    const messageEl = document.createElement('div');
    messageEl.className = `message ${type}`;
    messageEl.textContent = message;
    messageEl.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        padding: 12px 20px;
        border-radius: 6px;
        color: white;
        font-weight: 500;
        z-index: 1000;
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
        animation: slideIn 0.3s ease;
    `;
    
    if (type === 'warning') {
        messageEl.style.background = 'linear-gradient(135deg, #FF9800 0%, #F57C00 100%)';
    } else {
        messageEl.style.background = 'linear-gradient(135deg, #2196F3 0%, #1976D2 100%)';
    }
    
    document.body.appendChild(messageEl);
    
    // Remove after 3 seconds
    setTimeout(() => {
        messageEl.style.animation = 'slideOut 0.3s ease';
        setTimeout(() => {
            if (messageEl.parentNode) {
                messageEl.parentNode.removeChild(messageEl);
            }
        }, 300);
    }, 3000);
}

// Add animation styles
if (!document.getElementById('message-animations')) {
    const style = document.createElement('style');
    style.id = 'message-animations';
    style.textContent = `
        @keyframes slideIn {
            from {
                transform: translateX(100%);
                opacity: 0;
            }
            to {
                transform: translateX(0);
                opacity: 1;
            }
        }
        
        @keyframes slideOut {
            from {
                transform: translateX(0);
                opacity: 1;
            }
            to {
                transform: translateX(100%);
                opacity: 0;
            }
        }
    `;
    document.head.appendChild(style);
}










// Add a showMessage function for better UX
function showMessage(message, type = 'info') {
    // Remove any existing messages
    const existingMsg = document.querySelector('.download-message');
    if (existingMsg) existingMsg.remove();
    
    // Create message element
    const messageEl = document.createElement('div');
    messageEl.className = `download-message ${type}`;
    messageEl.textContent = message;
    messageEl.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        padding: 12px 20px;
        border-radius: 6px;
        color: white;
        font-weight: 500;
        z-index: 1000;
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
        animation: slideIn 0.3s ease;
    `;
    
    if (type === 'success') {
        messageEl.style.background = 'linear-gradient(135deg, #4CAF50 0%, #2E7D32 100%)';
    } else if (type === 'warning') {
        messageEl.style.background = 'linear-gradient(135deg, #FF9800 0%, #F57C00 100%)';
    } else if (type === 'error') {
        messageEl.style.background = 'linear-gradient(135deg, #F44336 0%, #D32F2F 100%)';
    } else {
        messageEl.style.background = 'linear-gradient(135deg, #2196F3 0%, #1976D2 100%)';
    }
    
    document.body.appendChild(messageEl);
    
    // Remove after 3 seconds
    setTimeout(() => {
        messageEl.style.animation = 'slideOut 0.3s ease';
        setTimeout(() => {
            if (messageEl.parentNode) {
                messageEl.parentNode.removeChild(messageEl);
            }
        }, 300);
    }, 3000);
}