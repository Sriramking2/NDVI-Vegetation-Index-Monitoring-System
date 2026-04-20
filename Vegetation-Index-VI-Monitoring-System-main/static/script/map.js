 
        // Initialize Map
        const map = L.map('map').setView([11.0, 77.0], 9);
        
        // Add Tile Layer
        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
            attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
        }).addTo(map);
        
        // Feature Group for drawn items
        const drawnItems = new L.FeatureGroup();
        map.addLayer(drawnItems);
        
        let polygonCoords = null;
        let currentImagePaths = {
            ndvi: null,
            rgb: null,
            savi: null,
            gndvi: null,
            evi: null
        };
        let placeName = '';
        
        // Initialize Draw Control
        const drawControl = new L.Control.Draw({
            draw: {
                polygon: {
                    allowIntersection: false,
                    showArea: true,
                    shapeOptions: {
                        color: '#2e7d32',
                        fillColor: '#2e7d32',
                        fillOpacity: 0.3,
                        weight: 3
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
            
            // Show success message
            showMessage('Polygon drawn successfully! Click "Generate Vegetation Analysis" to proceed.', 'success');
        });
        
        // Clear Map Function
        function clearMap() {
            drawnItems.clearLayers();
            polygonCoords = null;
            hideResults();
            showMessage('Map cleared. Draw a new polygon to analyze.', 'warning');
        }
        
        // Show/Hide Message
        function showMessage(text, type) {
            const messageDiv = document.getElementById('message');
            messageDiv.innerHTML = '';
            
            let icon = '';
            switch(type) {
                case 'success':
                    icon = '<i class="fas fa-check-circle"></i>';
                    break;
                case 'error':
                    icon = '<i class="fas fa-exclamation-circle"></i>';
                    break;
                case 'warning':
                    icon = '<i class="fas fa-exclamation-triangle"></i>';
                    break;
                case 'processing':
                    icon = '<div class="spinner"></div>';
                    break;
            }
            
            messageDiv.innerHTML = `${icon} ${text}`;
            messageDiv.className = '';
            messageDiv.classList.add(`message-${type}`);
            messageDiv.style.display = 'flex';
        }
        
        function hideMessage() {
            document.getElementById('message').style.display = 'none';
        }
        
        // Show/Hide Progress Bar
        function showProgress() {
            document.getElementById('progressContainer').style.display = 'block';
            document.getElementById('progressBar').style.width = '0%';
            document.getElementById('progressBar').textContent = '0%';
        }
        
        function updateProgress(percentage) {
            const progressBar = document.getElementById('progressBar');
            progressBar.style.width = percentage + '%';
            progressBar.textContent = Math.round(percentage) + '%';
        }
        
        function hideProgress() {
            document.getElementById('progressContainer').style.display = 'none';
        }
        
        // Hide Results
        function hideResults() {
            document.getElementById('resultsCard').style.display = 'none';
            const images = ['ndviImage', 'rgbImage', 'saviImage', 'gndviImage', 'eviImage'];
            images.forEach(id => {
                document.getElementById(id).style.display = 'none';
                document.getElementById(id.replace('Image', 'Placeholder')).style.display = 'flex';
            });
            // Reset image paths
            currentImagePaths = {
                ndvi: null,
                rgb: null,
                savi: null,
                gndvi: null,
                evi: null
            };
            placeName = '';
        }
        
        // Show Results
        function showResults(data) {
            document.getElementById('resultsCard').style.display = 'block';
            document.getElementById('resultsCard').classList.add('fade-in');
            
            // Update place and timestamp
            if (data.place) {
                placeName = data.place.replace(/_/g, ' ');
                document.getElementById('resultPlace').textContent = placeName;
            }
            if (data.timestamp) {
                document.getElementById('resultTimestamp').textContent = `Generated on: ${data.timestamp}`;
            }
            
            // Store image paths for download
            const images = {
                'ndvi': data.image || data.ndvi,
                'rgb': data.rgb,
                'savi': data.savi,
                'gndvi': data.gndvi,
                'evi': data.evi
            };
            
            // Display images and store paths
            for (const [key, src] of Object.entries(images)) {
                if (src) {
                    const imgElement = document.getElementById(key + 'Image');
                    const placeholder = document.getElementById(key + 'Placeholder');
                    
                    // Add cache busting parameter
                    imgElement.src = src + "?t=" + new Date().getTime();
                    imgElement.style.display = 'block';
                    placeholder.style.display = 'none';
                    
                    // Store the path for download
                    currentImagePaths[key] = src;
                }
            }
            
            // Enable download button if we have at least one image
            const downloadBtn = document.getElementById('downloadAllBtn');
            const hasImages = Object.values(currentImagePaths).some(path => path !== null);
            downloadBtn.disabled = !hasImages;
            
            // Scroll to results
            document.getElementById('resultsCard').scrollIntoView({ behavior: 'smooth' });
        }
        
        // Main NDVI Analysis Function
        function getNDVI() {
            if (!polygonCoords) {
                showMessage('Please draw a polygon on the map first!', 'warning');
                return;
            }
            
            const analyzeBtn = document.getElementById('analyzeBtn');
            const originalText = analyzeBtn.innerHTML;
            
            // Update button to show loading state
            analyzeBtn.innerHTML = '<div class="spinner"></div> Processing...';
            analyzeBtn.disabled = true;
            
            showMessage('Processing satellite data for selected area. This may take a moment...', 'processing');
            showProgress();
            updateProgress(10);
            
            fetch("/get_ndvi", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ polygon: polygonCoords })
            })
            .then(res => {
                if (!res.ok) {
                    throw new Error(`HTTP error! Status: ${res.status}`);
                }
                return res.json();
            })
            .then(data => {
                updateProgress(80);
                
                // Reset button
                analyzeBtn.innerHTML = originalText;
                analyzeBtn.disabled = false;
                
                if (data.no_data) {
                    showMessage('No satellite data available for the selected area. Try a different location or larger area.', 'error');
                    hideProgress();
                    return;
                }
                
                if (data.error) {
                    showMessage(`Error: ${data.error}`, 'error');
                    hideProgress();
                    return;
                }
                
                updateProgress(100);
                
                // Show success message
                showMessage('Analysis complete! Vegetation indices generated successfully.', 'success');
                
                // Display results
                showResults(data);
                
                // Show warnings if any
                if (data.warnings) {
                    setTimeout(() => {
                        showMessage(`Note: ${data.warnings}`, 'warning');
                    }, 2000);
                }
                
                setTimeout(hideProgress, 1000);
            })
            .catch(err => {
                console.error('Error:', err);
                analyzeBtn.innerHTML = originalText;
                analyzeBtn.disabled = false;
                showMessage('Server error. Please check your connection and try again.', 'error');
                hideProgress();
            });
        }
        
        // Download ALL images as ZIP
        async function downloadAllImages() {
            const downloadBtn = document.getElementById('downloadAllBtn');
            const originalText = downloadBtn.innerHTML;
            
            // Filter out null image paths
            const validImages = Object.entries(currentImagePaths)
                .filter(([key, path]) => path !== null);
            
            if (validImages.length === 0) {
                showMessage('No images available to download. Generate analysis first.', 'warning');
                return;
            }
            
            // Show processing state
            downloadBtn.innerHTML = '<div class="spinner"></div> Creating ZIP...';
            downloadBtn.disabled = true;
            showMessage('Creating ZIP file with all images...', 'processing');
            showProgress();
            updateProgress(10);
            
            try {
                const zip = new JSZip();
                const folder = zip.folder("ndvi_analysis");
                
                // Add README file
                const readmeContent = `NDVI Analysis Results\n===================\n\nLocation: ${placeName}\nDate: ${new Date().toLocaleString()}\n\nFiles included:\n`;
                
                let readmeText = readmeContent;
                
                // Download each image and add to zip
                for (let i = 0; i < validImages.length; i++) {
                    const [key, path] = validImages[i];
                    const imageName = `${key.toUpperCase()}.png`;
                    
                    updateProgress(10 + (i / validImages.length) * 70);
                    
                    try {
                        // Fetch the image
                        const response = await fetch(path);
                        if (!response.ok) {
                            throw new Error(`Failed to fetch ${key} image`);
                        }
                        
                        const blob = await response.blob();
                        
                        // Add to zip
                        folder.file(imageName, blob);
                        readmeText += `- ${imageName}: ${getImageDescription(key)}\n`;
                        
                    } catch (error) {
                        console.error(`Error downloading ${key}:`, error);
                        readmeText += `- ${imageName}: Failed to download\n`;
                    }
                }
                
                // Add README file
                folder.file("README.txt", readmeText);
                
                updateProgress(90);
                
                // Generate the zip file
                const zipBlob = await zip.generateAsync({type: "blob"}, (metadata) => {
                    updateProgress(90 + (metadata.percent / 100) * 10);
                });
                
                updateProgress(100);
                
                // Download the zip file
                const timestamp = new Date().toISOString().slice(0, 19).replace(/[:]/g, '-');
                const zipFilename = `ndvi_analysis_${timestamp}.zip`;
                
                saveAs(zipBlob, zipFilename);
                
                // Restore button state
                downloadBtn.innerHTML = originalText;
                downloadBtn.disabled = false;
                showMessage(`ZIP file downloaded successfully: ${zipFilename}`, 'success');
                
                setTimeout(hideProgress, 1000);
                
            } catch (error) {
                console.error('Error creating ZIP:', error);
                downloadBtn.innerHTML = originalText;
                downloadBtn.disabled = false;
                showMessage('Error creating ZIP file. Please try again.', 'error');
                hideProgress();
            }
        }
        
        // Helper function to get image descriptions
        function getImageDescription(key) {
            const descriptions = {
                'ndvi': 'Normalized Difference Vegetation Index',
                'rgb': 'True Color Satellite Image',
                'savi': 'Soil Adjusted Vegetation Index',
                'gndvi': 'Green Normalized Difference Vegetation Index',
                'evi': 'Enhanced Vegetation Index'
            };
            return descriptions[key] || key.toUpperCase();
        }
        
        // Download individual image
        function downloadIndividual(imageType) {
            const path = currentImage
                        if (!path) {
                showMessage(`${imageType.toUpperCase()} image not available for download.`, 'warning');
                return;
            }
            
            showMessage(`Downloading ${imageType.toUpperCase()} image...`, 'processing');
            
            // Extract filename from path
            const filename = path.split('/').pop() || `${imageType}.png`;
            
            // Create a temporary link and trigger download
            const link = document.createElement('a');
            link.href = path;
            link.download = filename;
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
            
            // Show success message
            setTimeout(() => {
                showMessage(`${imageType.toUpperCase()} image downloaded successfully!`, 'success');
            }, 500);
        }
        
        // Alternative: Download images one by one (without ZIP)
        async function downloadImagesIndividually() {
            const downloadBtn = document.getElementById('downloadAllBtn');
            const originalText = downloadBtn.innerHTML;
            
            // Filter out null image paths
            const validImages = Object.entries(currentImagePaths)
                .filter(([key, path]) => path !== null);
            
            if (validImages.length === 0) {
                showMessage('No images available to download. Generate analysis first.', 'warning');
                return;
            }
            
            // Show processing state
            downloadBtn.innerHTML = '<div class="spinner"></div> Preparing Downloads...';
            downloadBtn.disabled = true;
            showMessage(`Preparing to download ${validImages.length} images...`, 'processing');
            showProgress();
            
            let downloadedCount = 0;
            
            // Download each image individually
            for (let i = 0; i < validImages.length; i++) {
                const [key, path] = validImages[i];
                const filename = path.split('/').pop() || `${key}.png`;
                
                updateProgress((i / validImages.length) * 100);
                
                try {
                    // Create download link for each image
                    const link = document.createElement('a');
                    link.href = path;
                    link.download = filename;
                    link.style.display = 'none';
                    document.body.appendChild(link);
                    link.click();
                    document.body.removeChild(link);
                    
                    downloadedCount++;
                    
                    // Small delay between downloads
                    await new Promise(resolve => setTimeout(resolve, 300));
                    
                } catch (error) {
                    console.error(`Error downloading ${key}:`, error);
                }
            }
            
            updateProgress(100);
            
            // Restore button state
            downloadBtn.innerHTML = originalText;
            downloadBtn.disabled = false;
            
            if (downloadedCount > 0) {
                showMessage(`Successfully initiated download of ${downloadedCount} image(s)!`, 'success');
            } else {
                showMessage('Failed to download images. Please try again.', 'error');
            }
            
            setTimeout(hideProgress, 1000);
        }
        
        // Download via server-side ZIP creation
        async function downloadViaServer() {
            const downloadBtn = document.getElementById('downloadAllBtn');
            const originalText = downloadBtn.innerHTML;
            
            // Show processing state
            downloadBtn.innerHTML = '<div class="spinner"></div> Requesting ZIP...';
            downloadBtn.disabled = true;
            showMessage('Requesting ZIP file from server...', 'processing');
            
            try {
                // Send request to server to create ZIP
                const response = await fetch('/download_all_images', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        image_paths: currentImagePaths,
                        place_name: placeName
                    })
                });
                
                if (!response.ok) {
                    throw new Error('Server error');
                }
                
                // Get the ZIP blob
                const blob = await response.blob();
                
                // Create download link
                const url = window.URL.createObjectURL(blob);
                const link = document.createElement('a');
                link.href = url;
                link.download = `ndvi_analysis_${placeName.replace(/\s+/g, '_')}_${Date.now()}.zip`;
                document.body.appendChild(link);
                link.click();
                
                // Cleanup
                document.body.removeChild(link);
                window.URL.revokeObjectURL(url);
                
                // Restore button state
                downloadBtn.innerHTML = originalText;
                downloadBtn.disabled = false;
                showMessage('ZIP file downloaded successfully!', 'success');
                
            } catch (error) {
                console.error('Error downloading via server:', error);
                downloadBtn.innerHTML = originalText;
                downloadBtn.disabled = false;
                showMessage('Server-side ZIP creation failed. Using client-side method...', 'warning');
                
                // Fall back to client-side method
                setTimeout(() => {
                    downloadAllImages();
                }, 1000);
            }
        }
        
        // Show About Modal
        function showAbout() {
            alert('NDVI Analysis Tool v1.0\n\nThis tool uses Sentinel-2 satellite data to calculate various vegetation indices.\n\nNDVI Range:\n-1.0 to 0.0: Water, Snow, Clouds\n0.0 to 0.1: Bare Soil, Rocks\n0.1 to 0.5: Sparse Vegetation\n0.5 to 1.0: Dense Healthy Vegetation\n\nVegetation Indices:\n• NDVI: General vegetation health\n• RGB: True color satellite view\n• SAVI: Soil-adjusted vegetation index\n• GNDVI: Green vegetation index\n• EVI: Enhanced vegetation index');
        }
        
        // Show Help Modal
        function showHelp() {
            alert('Help & Instructions\n\n1. Use the polygon tool (top-right of map) to draw an area of interest\n2. Click "Generate Vegetation Analysis" to process satellite data\n3. View results including NDVI, RGB, SAVI, GNDVI, and EVI\n4. Click "Download All Images (ZIP)" to download all 5 vegetation indices\n5. Use individual download buttons for specific images\n6. View analysis history in the History section');
        }
        
        // Initialize
        window.onload = function() {
            showMessage('Draw a polygon on the map to begin vegetation analysis.', 'success');
            
            // Enable ZIP functionality if JSZip is loaded
            if (typeof JSZip !== 'undefined') {
                console.log('JSZip loaded successfully');
            } else {
                console.warn('JSZip not loaded, ZIP functionality may not work');
                showMessage('ZIP functionality requires JSZip library', 'warning');
            }
        };
  