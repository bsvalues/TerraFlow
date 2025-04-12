// Benton County GIS Map Viewer
document.addEventListener('DOMContentLoaded', () => {
    // Initialize the map
    window.map = L.map('map').setView([46.2362, -119.2478], 10); // Default to Benton County, WA
    const map = window.map;

    // Add OpenStreetMap base layer
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
        maxZoom: 19
    }).addTo(map);

    // Add Esri satellite imagery layer
    const esriSatellite = L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', {
        attribution: 'Tiles &copy; Esri &mdash; Source: Esri, i-cubed, USDA, USGS, AEX, GeoEye, Getmapping, Aerogrid, IGN, IGP, UPR-EGP, and the GIS User Community',
        maxZoom: 19
    });
    
    // Add USGS Topo layer
    const usgsTopoLayer = L.tileLayer('https://basemap.nationalmap.gov/arcgis/rest/services/USGSTopo/MapServer/tile/{z}/{y}/{x}', {
        attribution: 'Tiles &copy; USGS &mdash; National Map',
        maxZoom: 20
    });

    // Add layer control
    const baseMaps = {
        "OpenStreetMap": L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
            attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
            maxZoom: 19
        }),
        "Satellite": esriSatellite,
        "USGS Topo": usgsTopoLayer
    };

    // Add layer controls with different sections
    const layerControl = L.control.layers(baseMaps, {}, { 
        collapsed: false,
        position: 'topright',
        sortLayers: true
    }).addTo(map);

    // GeoJSON layers storage
    const geoJsonLayers = {};
    
    // Style function for GeoJSON features
    function styleFeature(feature) {
        return {
            fillColor: getRandomColor(),
            weight: 2,
            opacity: 1,
            color: '#333',
            fillOpacity: 0.7
        };
    }

    // Generate random colors for features
    function getRandomColor() {
        const colors = [
            '#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', 
            '#9467bd', '#8c564b', '#e377c2', '#7f7f7f', 
            '#bcbd22', '#17becf'
        ];
        return colors[Math.floor(Math.random() * colors.length)];
    }

    // Popup function for features
    function onEachFeature(feature, layer) {
        if (feature.properties) {
            const popupContent = createPopupContent(feature.properties);
            layer.bindPopup(popupContent);
        }
    }

    // Create HTML content for popups
    function createPopupContent(properties) {
        let content = '<div class="feature-popup">';
        
        // Loop through properties and create table rows
        content += '<table class="table table-sm table-striped">';
        for (const prop in properties) {
            if (properties.hasOwnProperty(prop)) {
                content += `<tr><th>${prop}</th><td>${properties[prop]}</td></tr>`;
            }
        }
        content += '</table></div>';
        
        return content;
    }

    // Load GeoJSON data
    function loadGeoJSON(fileId, fileName) {
        // If already loaded, just zoom to it
        if (geoJsonLayers[fileId]) {
            map.fitBounds(geoJsonLayers[fileId].getBounds());
            return;
        }
        
        fetch(`/map-data/${fileId}`)
            .then(response => {
                if (!response.ok) {
                    throw new Error('Network response was not ok');
                }
                return response.json();
            })
            .then(data => {
                // Add GeoJSON layer to map
                const layer = L.geoJSON(data, {
                    style: styleFeature,
                    onEachFeature: onEachFeature
                }).addTo(map);
                
                // Store the layer and add to controls
                geoJsonLayers[fileId] = layer;
                layerControl.addOverlay(layer, fileName);
                
                // Zoom to the layer
                map.fitBounds(layer.getBounds());
                
                // Update layer count
                updateLayerCount();
            })
            .catch(error => {
                console.error('Error loading GeoJSON:', error);
                showAlert('Error loading GeoJSON data. Please try again.', 'danger');
            });
    }

    // File selection handler
    document.getElementById('file-select').addEventListener('change', function() {
        const fileId = this.value;
        const fileName = this.options[this.selectedIndex].text;
        
        if (fileId) {
            loadGeoJSON(fileId, fileName);
        }
    });

    // Update layer count display
    function updateLayerCount() {
        const count = Object.keys(geoJsonLayers).length;
        document.getElementById('layer-count').textContent = count;
    }

    // Show alert message
    function showAlert(message, type) {
        const alertsContainer = document.getElementById('map-alerts');
        const alert = document.createElement('div');
        alert.className = `alert alert-${type} alert-dismissible fade show`;
        alert.innerHTML = `
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
        `;
        alertsContainer.appendChild(alert);
        
        // Auto dismiss after 5 seconds
        setTimeout(() => {
            alert.classList.remove('show');
            setTimeout(() => {
                alertsContainer.removeChild(alert);
            }, 150);
        }, 5000);
    }

    // Initialize map controls
    initMapControls(map);
});

// Initialize additional map controls
function initMapControls(map) {
    // Add scale bar
    L.control.scale().addTo(map);
    
    // Add zoom home button
    L.control.zoom({
        position: 'topleft',
        zoomInTitle: 'Zoom in',
        zoomOutTitle: 'Zoom out'
    }).addTo(map);
    
    // Add measurement tools
    new L.Control.Measure({
        position: 'bottomleft',
        primaryLengthUnit: 'feet',
        secondaryLengthUnit: 'miles',
        primaryAreaUnit: 'acres',
        secondaryAreaUnit: 'sqmiles'
    }).addTo(map);
    
    // Add coordinate display
    map.on('mousemove', function(e) {
        const lat = e.latlng.lat.toFixed(6);
        const lng = e.latlng.lng.toFixed(6);
        document.getElementById('map-coordinates').textContent = `Lat: ${lat}, Long: ${lng}`;
    });
}
