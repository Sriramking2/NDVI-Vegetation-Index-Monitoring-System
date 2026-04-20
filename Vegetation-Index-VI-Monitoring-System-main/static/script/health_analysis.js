// health_analysis.js

// Global variables
let map;
let drawnItems = new L.FeatureGroup();
let polygonCoords = null;
let currentAnalysisId = null;
let currentPlaceName = "Selected Area";
let isAnalyzing = false;

// Initialize Map
function initMap() {
    map = L.map('map').setView([20.5937, 78.9629], 5); // Center on India
    
    // Add Tile Layer
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '© OpenStreetMap contributors'
    }).addTo(map);
    
    // Feature Group for drawn items
    map.addLayer(drawnItems);
    
    // Initialize Draw Control
    const drawControl = new L.Control.Draw({
        draw: {
            polygon: {
                allowIntersection: false,
                showArea: true,
                shapeOptions: {
                    color: '#4CAF50',
                    weight: 3,
                    fillOpacity: 0.2,
                    fillColor: '#4CAF50'
                }
            },
            rectangle: false,
            circle: false,
            marker: false,
            polyline: false,
            circlemarker: false
        },
        edit: {
            featureGroup: drawnItems,
            edit: false
        }
    });
    
    map.addControl(drawControl);
    
    // Handle Draw Events
    map.on(L.Draw.Event.CREATED, function (e) {
        drawnItems.clearLayers();
        drawnItems.addLayer(e.layer);
        polygonCoords = e.layer.getLatLngs()[0].map(p => [p.lng, p.lat]);
        
        updateStatus('Area selected. Ready for analysis.', 'success');
        document.getElementById('analyzeBtn').disabled = false;
        
        // Show analyze button
        const analyzeBtn = document.getElementById('analyzeBtn');
        analyzeBtn.innerHTML = '<i class="fas fa-play-circle"></i><span>Start Analysis</span><div class="btn-subtext">Analyze Soil & Crop Health</div>';
    });
}

// Analyze Health (combined soil and crop)
async function analyzeHealth() {
    if (!polygonCoords) {
        showMessage('Please select an area on the map first!', 'error');
        return;
    }
    
    if (isAnalyzing) {
        showMessage('Analysis already in progress. Please wait...', 'warning');
        return;
    }
    
    isAnalyzing = true;
    const analyzeBtn = document.getElementById('analyzeBtn');
    const originalHTML = analyzeBtn.innerHTML;
    
    // Update button state
    analyzeBtn.innerHTML = '<div class="spinner"></div><span>Analyzing...</span>';
    analyzeBtn.disabled = true;
    
    // Reset metrics display
    resetMetrics();
    
    // Hide results grid initially
    document.getElementById('resultsGrid').style.display = 'none';
    
    // Update status
    updateStatus('Analyzing satellite data...', 'info');
    
    try {
        // Send request to backend
        const response = await fetch('/get_ndvi', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ polygon: polygonCoords })
        });
        
        if (!response.ok) {
            throw new Error(`Server responded with ${response.status}: ${response.statusText}`);
        }
        
        const data = await response.json();
        
        // Check for no data
        if (data.no_data) {
            showMessage('No cloud-free satellite imagery available for this location and time period.', 'error');
            return;
        }
        
        if (data.error) {
            showMessage(`Analysis failed: ${data.error}`, 'error');
            return;
        }
        
        // Store analysis ID
        currentAnalysisId = data.analysis_id;
        currentPlaceName = data.place || "Selected Area";
        
        // Update metrics display with actual data
        updateMetricsFromBackend(data);
        
        // Display results
        displayResults(data);
        
        // Show recommendations if available
        if (data.recommendations) {
            showRecommendations(data.recommendations);
        }
        
        showMessage('Soil and crop health analysis complete!', 'success');
        updateStatus('Analysis complete. Results ready.', 'success');
        
    } catch (error) {
        console.error('Analysis error:', error);
        showMessage(`Analysis failed: ${error.message}`, 'error');
        updateStatus('Analysis failed. Please try again.', 'error');
    } finally {
        // Restore button state
        analyzeBtn.innerHTML = originalHTML;
        analyzeBtn.disabled = false;
        isAnalyzing = false;
    }
}

// Update metrics from backend response
function updateMetricsFromBackend(data) {
    // Update Soil Metrics
    if (data.soil_metrics) {
        const soil = data.soil_metrics;
        
        document.getElementById('soilScore').textContent = formatValue(soil.soil_health_score);
        document.getElementById('soilMoisture').textContent = formatValue(soil.moisture_index);
        document.getElementById('soilOrganic').textContent = formatValue(soil.organic_matter);
        document.getElementById('soilTexture').textContent = formatValue(soil.texture_score);
        document.getElementById('soilPH').textContent = formatValue(soil.ph_level, false);
        
        // Color code soil score
        updateScoreColor('soilScore', soil.soil_health_score, 'soil');
    }
    
    // Update Crop Metrics
    if (data.crop_metrics) {
        const crop = data.crop_metrics;
        
        document.getElementById('cropScore').textContent = formatValue(crop.crop_health_score);
        document.getElementById('cropVigor').textContent = formatValue(crop.vigor_index);
        document.getElementById('cropStress').textContent = formatValue(crop.stress_level);
        document.getElementById('cropYield').textContent = formatValue(crop.yield_potential);
        document.getElementById('cropChlorophyll').textContent = formatValue(crop.chlorophyll_content);
        
        // Color code crop score
        updateScoreColor('cropScore', crop.crop_health_score, 'crop');
    }
    
    // Update place name if available
    if (data.place) {
        document.querySelector('.section-header h2').innerHTML = `<i class="fas fa-chart-line"></i> Health Analysis - ${data.place}`;
    }
}

// Format value for display
function formatValue(value, addPercent = true) {
    if (value === null || value === undefined) return '--';
    const formatted = typeof value === 'number' ? value.toFixed(1) : value;
    return addPercent ? `${formatted}%` : formatted;
}

// Update score color based on value
function updateScoreColor(elementId, score, type) {
    const element = document.getElementById(elementId);
    if (!element) return;
    
    score = parseFloat(score);
    
    if (type === 'soil') {
        if (score >= 80) {
            element.style.background = 'linear-gradient(135deg, #4CAF50 0%, #2E7D32 100%)';
            element.style.color = 'white';
        } else if (score >= 60) {
            element.style.background = 'linear-gradient(135deg, #FFC107 0%, #FF9800 100%)';
            element.style.color = '#333';
        } else if (score >= 40) {
            element.style.background = 'linear-gradient(135deg, #FF9800 0%, #F57C00 100%)';
            element.style.color = 'white';
        } else {
            element.style.background = 'linear-gradient(135deg, #F44336 0%, #D32F2F 100%)';
            element.style.color = 'white';
        }
    } else { // crop
        if (score >= 85) {
            element.style.background = 'linear-gradient(135deg, #4CAF50 0%, #2E7D32 100%)';
            element.style.color = 'white';
        } else if (score >= 70) {
            element.style.background = 'linear-gradient(135deg, #8BC34A 0%, #689F38 100%)';
            element.style.color = 'white';
        } else if (score >= 55) {
            element.style.background = 'linear-gradient(135deg, #FFC107 0%, #FFA000 100%)';
            element.style.color = '#333';
        } else if (score >= 40) {
            element.style.background = 'linear-gradient(135deg, #FF9800 0%, #F57C00 100%)';
            element.style.color = 'white';
        } else {
            element.style.background = 'linear-gradient(135deg, #F44336 0%, #D32F2F 100%)';
            element.style.color = 'white';
        }
    }
}

// Display results from backend
function displayResults(data) {
    // Show results grid
    const resultsGrid = document.getElementById('resultsGrid');
    resultsGrid.style.display = 'grid';
    
    // Function to update result card
    const updateResultCard = (imageId, placeholderId, statusId, imageUrl, statusText, statusIcon) => {
        const imageElement = document.getElementById(imageId);
        const placeholderElement = document.getElementById(placeholderId);
        const statusElement = document.getElementById(statusId);
        
        if (imageUrl) {
            imageElement.src = imageUrl + '?t=' + new Date().getTime();
            imageElement.style.display = 'block';
            if (placeholderElement) placeholderElement.style.display = 'none';
        } else {
            imageElement.style.display = 'none';
            if (placeholderElement) placeholderElement.style.display = 'flex';
        }
        
        if (statusElement) {
            statusElement.innerHTML = `<i class="fas ${statusIcon}"></i> <span>${statusText}</span>`;
            
            // Update status color
            if (statusText.includes('Ready') || statusText.includes('Complete')) {
                statusElement.style.color = '#4CAF50';
            } else if (statusText.includes('Failed')) {
                statusElement.style.color = '#F44336';
            }
        }
    };
    
    // Update each result card
    updateResultCard(
        'soilImage', 'soilPlaceholder', 'soilStatus',
        data.soil_health, 
        data.soil_health ? 'Ready' : 'Not Available',
        data.soil_health ? 'fa-check-circle' : 'fa-times-circle'
    );
    
    updateResultCard(
        'cropImage', 'cropPlaceholder', 'cropStatus',
        data.crop_health, 
        data.crop_health ? 'Ready' : 'Not Available',
        data.crop_health ? 'fa-check-circle' : 'fa-times-circle'
    );
    
    updateResultCard(
        'ndviImage', 'ndviPlaceholder', 'ndviStatus',
        data.image, 
        data.image ? 'Ready' : 'Not Available',
        data.image ? 'fa-check-circle' : 'fa-times-circle'
    );
    
    updateResultCard(
        'saviImage', 'saviPlaceholder', 'saviStatus',
        data.savi, 
        data.savi ? 'Ready' : 'Not Available',
        data.savi ? 'fa-check-circle' : 'fa-times-circle'
    );
    
    // Also update RGB, GNDVI, EVI if you add them later
    if (data.rgb) {
        // You can add RGB display if needed
        console.log('RGB image available:', data.rgb);
    }
}

// Show recommendations
function showRecommendations(recommendations) {
    // Create or update recommendations display
    let recContainer = document.getElementById('recommendationsContainer');
    if (!recContainer) {
        recContainer = document.createElement('div');
        recContainer.id = 'recommendationsContainer';
        recContainer.className = 'recommendations-container';
        recContainer.innerHTML = '<h3><i class="fas fa-lightbulb"></i> Recommendations</h3><div id="recommendationsList"></div>';
        document.querySelector('.analysis-section .section-container').appendChild(recContainer);
    }
    
    const listContainer = document.getElementById('recommendationsList');
    if (listContainer) {
        listContainer.innerHTML = '';
        
        if (Array.isArray(recommendations) && recommendations.length > 0) {
            recommendations.forEach(rec => {
                const recItem = document.createElement('div');
                recItem.className = 'recommendation-item';
                
                // Add appropriate icon based on recommendation type
                let icon = 'fa-info-circle';
                let colorClass = 'info';
                
                if (rec.includes('🚨') || rec.includes('Urgent') || rec.includes('Critical')) {
                    icon = 'fa-exclamation-circle';
                    colorClass = 'critical';
                } else if (rec.includes('⚠️')) {
                    icon = 'fa-exclamation-triangle';
                    colorClass = 'warning';
                } else if (rec.includes('✅')) {
                    icon = 'fa-check-circle';
                    colorClass = 'success';
                }
                
                recItem.innerHTML = `
                    <div class="rec-icon ${colorClass}">
                        <i class="fas ${icon}"></i>
                    </div>
                    <div class="rec-text">${rec}</div>
                `;
                
                listContainer.appendChild(recItem);
            });
        } else {
            listContainer.innerHTML = '<div class="no-recommendations">No specific recommendations available.</div>';
        }
    }
}

// Update status message
function updateStatus(message, type = 'info') {
    const statusIndicator = document.getElementById('statusIndicator');
    if (!statusIndicator) return;
    
    let icon = 'fa-info-circle';
    let color = '#2196F3';
    
    switch (type) {
        case 'success':
            icon = 'fa-check-circle';
            color = '#4CAF50';
            break;
        case 'error':
            icon = 'fa-exclamation-circle';
            color = '#F44336';
            break;
        case 'warning':
            icon = 'fa-exclamation-triangle';
            color = '#FF9800';
            break;
    }
    
    statusIndicator.innerHTML = `<i class="fas ${icon}"></i> <span>${message}</span>`;
    statusIndicator.style.color = color;
}

// Show message toast
function showMessage(text, type = 'info') {
    // Remove existing message
    const existingMessage = document.getElementById('messageToast');
    if (existingMessage) {
        existingMessage.remove();
    }
    
    // Create message element
    const messageEl = document.createElement('div');
    messageEl.id = 'messageToast';
    messageEl.className = 'message-toast';
    
    // Set style based on type
    let bgColor = '#2196F3';
    let icon = 'fa-info-circle';
    
    switch (type) {
        case 'success':
            bgColor = '#4CAF50';
            icon = 'fa-check-circle';
            break;
        case 'error':
            bgColor = '#F44336';
            icon = 'fa-times-circle';
            break;
        case 'warning':
            bgColor = '#FF9800';
            icon = 'fa-exclamation-triangle';
            break;
    }
    
    messageEl.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        padding: 15px 25px;
        border-radius: 8px;
        background: ${bgColor};
        color: white;
        font-weight: 500;
        z-index: 10000;
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
        animation: slideIn 0.3s ease;
        display: flex;
        align-items: center;
        gap: 10px;
        max-width: 400px;
    `;
    
    messageEl.innerHTML = `<i class="fas ${icon}"></i><span>${text}</span>`;
    
    document.body.appendChild(messageEl);
    
    // Add CSS for animation
    if (!document.getElementById('messageAnimation')) {
        const style = document.createElement('style');
        style.id = 'messageAnimation';
        style.textContent = `
            @keyframes slideIn {
                from { transform: translateX(100%); opacity: 0; }
                to { transform: translateX(0); opacity: 1; }
            }
            @keyframes slideOut {
                from { transform: translateX(0); opacity: 1; }
                to { transform: translateX(100%); opacity: 0; }
            }
            .spinner {
                border: 2px solid rgba(255,255,255,0.3);
                border-top: 2px solid white;
                border-radius: 50%;
                width: 16px;
                height: 16px;
                animation: spin 1s linear infinite;
                display: inline-block;
                vertical-align: middle;
                margin-right: 8px;
            }
            @keyframes spin {
                0% { transform: rotate(0deg); }
                100% { transform: rotate(360deg); }
            }
        `;
        document.head.appendChild(style);
    }
    
    // Remove message after 4 seconds
    setTimeout(() => {
        if (messageEl.parentNode) {
            messageEl.style.animation = 'slideOut 0.3s ease';
            setTimeout(() => {
                if (messageEl.parentNode) {
                    messageEl.parentNode.removeChild(messageEl);
                }
            }, 300);
        }
    }, 4000);
}

// Reset metrics display
function resetMetrics() {
    const metrics = [
        'soilScore', 'soilMoisture', 'soilOrganic', 'soilTexture', 'soilPH',
        'cropScore', 'cropVigor', 'cropStress', 'cropYield', 'cropChlorophyll'
    ];
    
    metrics.forEach(id => {
        const element = document.getElementById(id);
        if (element) {
            if (id.includes('Score')) {
                element.textContent = '--';
                element.style.background = '';
                element.style.color = '';
            } else if (id === 'soilPH') {
                element.textContent = '--';
            } else {
                element.textContent = '--%';
            }
        }
    });
    
    // Hide results grid
    document.getElementById('resultsGrid').style.display = 'none';
    
    // Reset status
    updateStatus('Select an area on the map to begin analysis', 'info');
    
    // Clear recommendations
    const recContainer = document.getElementById('recommendationsContainer');
    if (recContainer) {
        recContainer.remove();
    }
}

// Clear map and reset
function clearMap() {
    drawnItems.clearLayers();
    polygonCoords = null;
    
    // Reset metrics
    resetMetrics();
    
    // Reset button
    const analyzeBtn = document.getElementById('analyzeBtn');
    analyzeBtn.disabled = true;
    
    showMessage('Map cleared. Select a new area to analyze.', 'info');
}

// Export analysis data
async function exportAnalysis() {
    if (!currentAnalysisId) {
        showMessage('No analysis to export. Please run an analysis first.', 'warning');
        return;
    }
    
    try {
        // Get detailed metrics
        const response = await fetch(`/get_detailed_health_metrics?id=${currentAnalysisId}`);
        const data = await response.json();
        
        if (!data.success) {
            throw new Error(data.error || 'Failed to export analysis');
        }
        
        // Create export data
        const exportData = {
            analysis_id: currentAnalysisId,
            place_name: data.place_name,
            datetime: data.datetime,
            soil_metrics: data.soil_metrics,
            crop_metrics: data.crop_metrics,
            recommendations: data.recommendations,
            interpretation: data.interpretation,
            export_date: new Date().toISOString()
        };
        
        // Create downloadable JSON
        const dataStr = JSON.stringify(exportData, null, 2);
        const dataBlob = new Blob([dataStr], { type: 'application/json' });
        const url = URL.createObjectURL(dataBlob);
        
        const link = document.createElement('a');
        link.href = url;
        link.download = `health_analysis_${data.place_name}_${data.datetime.replace(/[: ]/g, '-')}.json`;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        
        showMessage('Health analysis data exported successfully!', 'success');
        
    } catch (error) {
        console.error('Export error:', error);
        showMessage(`Export failed: ${error.message}`, 'error');
    }
}

// Get health statistics
async function getHealthStats() {
    try {
        const response = await fetch('/get_health_stats');
        const data = await response.json();
        
        if (data.success) {
            console.log('Health statistics:', data.stats);
            // You can display these stats in your UI if needed
            return data.stats;
        }
    } catch (error) {
        console.error('Error getting health stats:', error);
    }
}

// Initialize everything when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    // Initialize map
    initMap();
    
    // Set up event listeners
    const analyzeBtn = document.getElementById('analyzeBtn');
    const exportBtn = document.getElementById('exportBtn');
    const clearBtn = document.querySelector('.map-control-btn');
    
    if (analyzeBtn) {
        analyzeBtn.addEventListener('click', analyzeHealth);
    }
    
    if (exportBtn) {
        exportBtn.addEventListener('click', exportAnalysis);
    }
    
    if (clearBtn) {
        clearBtn.addEventListener('click', clearMap);
    }
    
    // Initialize status
    updateStatus('Select an area on the map to begin analysis', 'info');
    
    // Load health statistics
    setTimeout(getHealthStats, 1000);
    
    // Add custom CSS for spinner
    if (!document.getElementById('spinnerStyle')) {
        const style = document.createElement('style');
        style.id = 'spinnerStyle';
        style.textContent = `
            .spinner {
                border: 2px solid rgba(76, 175, 80, 0.3);
                border-top: 2px solid #4CAF50;
                border-radius: 50%;
                width: 20px;
                height: 20px;
                animation: spin 1s linear infinite;
                display: inline-block;
                margin-right: 10px;
                vertical-align: middle;
            }
            
            .recommendations-container {
                margin-top: 20px;
                padding: 20px;
                background: #f5f5f5;
                border-radius: 8px;
                border-left: 4px solid #4CAF50;
            }
            
            .recommendations-container h3 {
                margin-top: 0;
                color: #333;
                font-size: 18px;
                margin-bottom: 15px;
            }
            
            .recommendation-item {
                display: flex;
                align-items: flex-start;
                gap: 10px;
                padding: 10px;
                background: white;
                border-radius: 6px;
                margin-bottom: 10px;
                border-left: 4px solid #2196F3;
            }
            
            .recommendation-item.critical {
                border-left-color: #F44336;
            }
            
            .recommendation-item.warning {
                border-left-color: #FF9800;
            }
            
            .recommendation-item.success {
                border-left-color: #4CAF50;
            }
            
            .rec-icon {
                font-size: 16px;
                margin-top: 2px;
            }
            
            .rec-icon.critical { color: #F44336; }
            .rec-icon.warning { color: #FF9800; }
            .rec-icon.success { color: #4CAF50; }
            .rec-icon.info { color: #2196F3; }
            
            .rec-text {
                flex: 1;
                font-size: 14px;
                line-height: 1.5;
            }
            
            .no-recommendations {
                color: #666;
                font-style: italic;
                padding: 10px;
                text-align: center;
            }
            
            .message-toast {
                position: fixed;
                top: 20px;
                right: 20px;
                padding: 15px 25px;
                border-radius: 8px;
                color: white;
                font-weight: 500;
                z-index: 10000;
                box-shadow: 0 4px 12px rgba(0,0,0,0.15);
                animation: slideIn 0.3s ease;
                display: flex;
                align-items: center;
                gap: 10px;
                max-width: 400px;
            }
            
            @keyframes slideIn {
                from { transform: translateX(100%); opacity: 0; }
                to { transform: translateX(0); opacity: 1; }
            }
            
            @keyframes slideOut {
                from { transform: translateX(0); opacity: 1; }
                to { transform: translateX(100%); opacity: 0; }
            }
            
            @keyframes spin {
                0% { transform: rotate(0deg); }
                100% { transform: rotate(360deg); }
            }
        `;
        document.head.appendChild(style);
    }
});