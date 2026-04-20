
        let trendChart, locationChart, fileChart;
        let lastUpdateTime = null;

        // Initialize on page load
        document.addEventListener('DOMContentLoaded', function() {
            loadDashboard();
            loadHealthStatus();
            loadCharts();
            startAutoRefresh();
        });

        // Load dashboard statistics
        async function loadDashboard() {
            try {
                const response = await fetch('/api/statistics/dashboard');
                const data = await response.json();
                
                if (data.success) {
                    updateDashboard(data.statistics);
                    lastUpdateTime = new Date().toLocaleTimeString();
                    document.getElementById('lastUpdated').textContent = lastUpdateTime;
                }
            } catch (error) {
                console.error('Error loading dashboard:', error);
            }
        }

        // Update dashboard with statistics
        function updateDashboard(stats) {
            const dashboardStats = document.getElementById('dashboardStats');
            
            dashboardStats.innerHTML = `
                <div class="stat-card highlight">
                    <div class="stat-header">
                        <div class="stat-icon total">
                            <i class="fas fa-chart-bar"></i>
                        </div>
                        <div>
                            <div class="stat-title">Total Analyses</div>
                            <div class="stat-value">${stats.total_analyses}</div>
                            <div class="stat-subtitle">Since beginning</div>
                        </div>
                    </div>
                </div>
                
                <div class="stat-card">
                    <div class="stat-header">
                        <div class="stat-icon today">
                            <i class="fas fa-calendar-day"></i>
                        </div>
                        <div>
                            <div class="stat-title">Today's Analyses</div>
                            <div class="stat-value">${stats.today_analyses}</div>
                            <div class="stat-subtitle">${stats.week_analyses} this week</div>
                        </div>
                    </div>
                </div>
                
                <div class="stat-card">
                    <div class="stat-header">
                        <div class="stat-icon locations">
                            <i class="fas fa-map-marked-alt"></i>
                        </div>
                        <div>
                            <div class="stat-title">Unique Locations</div>
                            <div class="stat-value">${stats.unique_locations}</div>
                            <div class="stat-subtitle">${stats.top_locations.length} active areas</div>
                        </div>
                    </div>
                </div>
                
                <div class="stat-card">
                    <div class="stat-header">
                        <div class="stat-icon storage">
                            <i class="fas fa-hdd"></i>
                        </div>
                        <div>
                            <div class="stat-title">Storage Used</div>
                            <div class="stat-value">${formatBytes(stats.system_info.static_dir_size)}</div>
                            <div class="stat-subtitle">${stats.file_stats.total_images} files</div>
                        </div>
                    </div>
                </div>
                
                <div class="stat-card">
                    <div class="stat-header">
                        <div class="stat-icon health">
                            <i class="fas fa-heartbeat"></i>
                        </div>
                        <div>
                            <div class="stat-title">System Health</div>
                            <div class="stat-value">${stats.system_info.earth_engine_status ? '✓' : '✗'}</div>
                            <div class="stat-subtitle">Earth Engine ${stats.system_info.earth_engine_status ? 'Ready' : 'Offline'}</div>
                        </div>
                    </div>
                </div>
                
                <div class="stat-card">
                    <div class="stat-header">
                        <div class="stat-icon uptime">
                            <i class="fas fa-clock"></i>
                        </div>
                        <div>
                            <div class="stat-title">Server Uptime</div>
                            <div class="stat-value">${stats.system_info.uptime}</div>
                            <div class="stat-subtitle">Since ${formatTime(stats.system_info.server_time)}</div>
                        </div>
                    </div>
                </div>
            `;
        }

        // Load health status
        async function loadHealthStatus() {
            try {
                const response = await fetch('/api/statistics/system_health');
                const data = await response.json();
                
                if (data.success) {
                    updateHealthStatus(data.health_check);
                }
            } catch (error) {
                console.error('Error loading health status:', error);
            }
        }

        // Update health status display
        function updateHealthStatus(health) {
            const healthStatus = document.getElementById('healthStatus');
            
            healthStatus.innerHTML = `
                <div class="health-card">
                    <div class="health-header">
                        <div class="health-icon ${health.database.status === 'connected' ? 'healthy' : 'error'}">
                            <i class="fas fa-database"></i>
                        </div>
                        <div class="health-title">Database</div>
                    </div>
                    <div class="health-items">
                        <div class="health-item">
                            <span class="item-label">Status</span>
                            <span class="status-badge ${health.database.status === 'connected' ? 'healthy' : 'error'}">
                                ${health.database.status}
                            </span>
                        </div>
                        <div class="health-item">
                            <span class="item-label">Size</span>
                            <span class="item-value">${health.database.size_human}</span>
                        </div>
                        <div class="health-item">
                            <span class="item-label">Records</span>
                            <span class="item-value">${health.database.record_count}</span>
                        </div>
                    </div>
                </div>
                
                <div class="health-card">
                    <div class="health-header">
                        <div class="health-icon ${health.storage.writable ? 'healthy' : 'warning'}">
                            <i class="fas fa-folder-open"></i>
                        </div>
                        <div class="health-title">Storage</div>
                    </div>
                    <div class="health-items">
                        <div class="health-item">
                            <span class="item-label">Status</span>
                            <span class="status-badge ${health.storage.writable ? 'healthy' : 'warning'}">
                                ${health.storage.writable ? 'Writable' : 'Read-only'}
                            </span>
                        </div>
                        <div class="health-item">
                            <span class="item-label">Size</span>
                            <span class="item-value">${health.storage.size_human}</span>
                        </div>
                        <div class="health-item">
                            <span class="item-label">Files</span>
                            <span class="item-value">${health.storage.file_count}</span>
                        </div>
                    </div>
                </div>
                
                <div class="health-card">
                    <div class="health-header">
                        <div class="health-icon ${health.services.earth_engine.available ? 'healthy' : 'warning'}">
                            <i class="fas fa-satellite"></i>
                        </div>
                        <div class="health-title">Services</div>
                    </div>
                    <div class="health-items">
                        <div class="health-item">
                            <span class="item-label">Earth Engine</span>
                            <span class="status-badge ${health.services.earth_engine.available ? 'healthy' : 'warning'}">
                                ${health.services.earth_engine.available ? 'Online' : 'Offline'}
                            </span>
                        </div>
                        <div class="health-item">
                            <span class="item-label">Internet</span>
                            <span class="status-badge ${health.services.internet.status === 'connected' ? 'healthy' : 'error'}">
                                ${health.services.internet.status}
                            </span>
                        </div>
                        <div class="health-item">
                                                        <span class="item-label">Geolocation</span>
                            <span class="status-badge healthy">
                                Online
                            </span>
                        </div>
                    </div>
                </div>
            `;
        }

        // Load all charts
        async function loadCharts() {
            await loadTrendChart();
            await loadLocationChart();
            await loadFileStats();
        }

        // Load trend chart
        async function loadTrendChart() {
            const period = document.getElementById('periodSelect').value;
            
            try {
                const response = await fetch(`/api/statistics/analyses_by_date?period=${period}`);
                const data = await response.json();
                
                if (data.success) {
                    updateTrendChart(data.data, period);
                }
            } catch (error) {
                console.error('Error loading trend chart:', error);
            }
        }

        // Update trend chart
        function updateTrendChart(data, period) {
            const ctx = document.getElementById('trendChart').getContext('2d');
            
            if (trendChart) {
                trendChart.destroy();
            }
            
            const labels = data.map(item => period === 'week' ? formatDate(item.date) : item.period);
            const counts = data.map(item => item.count);
            
            trendChart = new Chart(ctx, {
                type: 'line',
                data: {
                    labels: labels,
                    datasets: [{
                        label: 'Number of Analyses',
                        data: counts,
                        borderColor: '#2e7d32',
                        backgroundColor: 'rgba(46, 125, 50, 0.1)',
                        borderWidth: 2,
                        fill: true,
                        tension: 0.4
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: {
                            position: 'top',
                        },
                        title: {
                            display: true,
                            text: `Analyses Trend (${period === 'week' ? 'Last 7 Days' : period === 'month' ? 'Last 12 Months' : 'Yearly'})`
                        }
                    },
                    scales: {
                        y: {
                            beginAtZero: true,
                            title: {
                                display: true,
                                text: 'Number of Analyses'
                            }
                        }
                    }
                }
            });
        }

        // Load location chart
        async function loadLocationChart() {
            try {
                const response = await fetch('/api/statistics/location_distribution');
                const data = await response.json();
                
                if (data.success) {
                    updateLocationChart(data.data);
                }
            } catch (error) {
                console.error('Error loading location chart:', error);
            }
        }

        // Update location chart
        function updateLocationChart(data) {
            const ctx = document.getElementById('locationChart').getContext('2d');
            
            if (locationChart) {
                locationChart.destroy();
            }
            
            const labels = data.map(item => item.name);
            const counts = data.map(item => item.count);
            const colors = generateColors(data.length);
            
            locationChart = new Chart(ctx, {
                type: 'pie',
                data: {
                    labels: labels,
                    datasets: [{
                        data: counts,
                        backgroundColor: colors,
                        borderWidth: 1
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: {
                            position: 'right',
                        },
                        title: {
                            display: true,
                            text: `Location Distribution (${data.length} locations)`
                        }
                    }
                }
            });
        }

        // Load file statistics
        async function loadFileStats() {
            try {
                const response = await fetch('/api/statistics/dashboard');
                const data = await response.json();
                
                if (data.success) {
                    updateFileChart(data.statistics.file_stats);
                }
            } catch (error) {
                console.error('Error loading file stats:', error);
            }
        }

        // Update file chart
        function updateFileChart(fileStats) {
            const ctx = document.getElementById('fileChart').getContext('2d');
            
            if (fileChart) {
                fileChart.destroy();
            }
            
            const labels = ['NDVI', 'RGB', 'SAVI', 'GNDVI', 'EVI', 'GeoTIFF'];
            const data = [
                fileStats.ndvi_images || 0,
                fileStats.rgb_images || 0,
                fileStats.savi_images || 0,
                fileStats.gndvi_images || 0,
                fileStats.evi_images || 0,
                fileStats.geotiff_files || 0
            ];
            
            fileChart = new Chart(ctx, {
                type: 'bar',
                data: {
                    labels: labels,
                    datasets: [{
                        label: 'Number of Files',
                        data: data,
                        backgroundColor: [
                            'rgba(139, 0, 0, 0.7)',    // NDVI - Dark Red
                            'rgba(33, 150, 243, 0.7)', // RGB - Blue
                            'rgba(139, 69, 19, 0.7)',  // SAVI - Brown
                            'rgba(39, 174, 96, 0.7)',  // GNDVI - Green
                            'rgba(75, 0, 130, 0.7)',   // EVI - Purple
                            'rgba(255, 152, 0, 0.7)'   // GeoTIFF - Orange
                        ],
                        borderColor: [
                            'rgb(139, 0, 0)',
                            'rgb(33, 150, 243)',
                            'rgb(139, 69, 19)',
                            'rgb(39, 174, 96)',
                            'rgb(75, 0, 130)',
                            'rgb(255, 152, 0)'
                        ],
                        borderWidth: 1
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: {
                            display: false
                        },
                        title: {
                            display: true,
                            text: `File Statistics (Total: ${fileStats.total_images || 0} images)`
                        }
                    },
                    scales: {
                        y: {
                            beginAtZero: true,
                            title: {
                                display: true,
                                text: 'Number of Files'
                            }
                        }
                    }
                }
            });
        }

        // Helper functions
        function formatBytes(bytes, decimals = 2) {
            if (bytes === 0) return '0 Bytes';
            
            const k = 1024;
            const dm = decimals < 0 ? 0 : decimals;
            const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB'];
            
            const i = Math.floor(Math.log(bytes) / Math.log(k));
            
            return parseFloat((bytes / Math.pow(k, i)).toFixed(dm)) + ' ' + sizes[i];
        }

        function formatDate(dateString) {
            const date = new Date(dateString);
            return date.toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric' });
        }

        function formatTime(dateString) {
            const date = new Date(dateString);
            return date.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' });
        }

        function generateColors(count) {
            const colors = [];
            const hueStep = 360 / count;
            
            for (let i = 0; i < count; i++) {
                const hue = i * hueStep;
                colors.push(`hsl(${hue}, 70%, 60%)`);
            }
            
            return colors;
        }

        // Auto-refresh every 30 seconds
        function startAutoRefresh() {
            setInterval(() => {
                if (document.visibilityState === 'visible') {
                    loadDashboard();
                    loadHealthStatus();
                }
            }, 30000);
        }

        // Period selector change
        document.getElementById('periodSelect').addEventListener('change', loadTrendChart);

        // Manual refresh button
        window.refreshAll = function() {
            loadDashboard();
            loadHealthStatus();
            loadCharts();
            document.getElementById('lastUpdated').textContent = new Date().toLocaleTimeString();
        };
  