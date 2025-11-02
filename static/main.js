// Global variables
let map;
let markers = [];
let routeLayer = null;
let spotIdCounter = 1;

// Initialize the map when page loads
function initMap() {
    // Create map centered on a default location (Paris as example)
    map = L.map('map').setView([48.8566, 2.3522], 13);

    // Add OpenStreetMap tile layer
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '© OpenStreetMap contributors',
        maxZoom: 19
    }).addTo(map);

    // Add click event listener to map
    map.on('click', function(e) {
        addMarker(e.latlng.lat, e.latlng.lng);
    });

    // Event listeners for buttons
    document.getElementById('planRoute').addEventListener('click', planRoute);
    document.getElementById('clearAll').addEventListener('click', clearAllSpots);
    document.getElementById('clearRoute').addEventListener('click', clearRoute);
    
    // Sidebar toggle
    document.getElementById('toggleSidebar').addEventListener('click', toggleSidebar);

    console.log('Map initialized successfully');
}

// Add a marker to the map
function addMarker(lat, lng) {
    const id = spotIdCounter++;
    const marker = L.marker([lat, lng], {
        icon: L.icon({
            iconUrl: 'https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-blue.png',
            shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-shadow.png',
            iconSize: [25, 41],
            iconAnchor: [12, 41],
            popupAnchor: [1, -34],
            shadowSize: [41, 41]
        })
    }).addTo(map);

    marker.bindPopup(`
        <strong>Spot ${id}</strong><br>
        📍 Lat: ${lat.toFixed(4)}, Lng: ${lng.toFixed(4)}<br>
        <button onclick="removeMarker(${id})" style="margin-top: 5px; padding: 5px 10px; background: #ff4444; color: white; border: none; border-radius: 4px; cursor: pointer;">❌ Remove</button>
    `);

    markers.push({
        id: id,
        lat: lat,
        lng: lng,
        marker: marker
    });

    // Enable the "Plan Route" button if we have at least 2 markers
    const planBtn = document.getElementById('planRoute');
    if (markers.length >= 2) {
        planBtn.disabled = false;
    }

    showStatus(`Added Spot ${id}`, 'success');
}

// Remove a marker
function removeMarker(id) {
    const index = markers.findIndex(m => m.id === id);
    if (index !== -1) {
        map.removeLayer(markers[index].marker);
        markers.splice(index, 1);
        
        // Disable "Plan Route" button if we have less than 2 markers
        const planBtn = document.getElementById('planRoute');
        if (markers.length < 2) {
            planBtn.disabled = true;
        }
        
        showStatus('Spot removed', 'success');
    }
}

// Clear all spots
function clearAllSpots() {
    markers.forEach(m => map.removeLayer(m.marker));
    markers = [];
    spotIdCounter = 1;
    document.getElementById('planRoute').disabled = true;
    clearRoute();
    showStatus('All spots cleared', 'success');
}

// Clear the route
function clearRoute() {
    if (routeLayer) {
        map.removeLayer(routeLayer);
        routeLayer = null;
    }
    document.getElementById('routeInfo').classList.remove('show');
}

// Show status message
function showStatus(message, type = 'success') {
    const statusEl = document.getElementById('status');
    statusEl.textContent = message;
    statusEl.className = `status ${type} show`;
    
    setTimeout(() => {
        statusEl.classList.remove('show');
    }, 3000);
}

// Toggle sidebar visibility
function toggleSidebar() {
    const sidebar = document.getElementById('sidebar');
    sidebar.classList.toggle('hidden');
    
    // Trigger map resize when sidebar is toggled to fix map rendering
    setTimeout(() => {
        map.invalidateSize();
    }, 300);
}

// Plan the route
async function planRoute() {
    if (markers.length < 2) {
        showStatus('Please add at least 2 spots', 'error');
        return;
    }

    // Disable button during request
    const planBtn = document.getElementById('planRoute');
    planBtn.disabled = true;
    planBtn.textContent = '⏳ Planning...';

    // Collect coordinates
    const coordinates = markers.map(m => [m.lat, m.lng]);

    try {
        showStatus('Computing optimal route...', 'success');

        // Send request to backend
        const response = await fetch('/plan_route', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ coordinates })
        });

        const data = await response.json();

        if (!response.ok || !data.success) {
            throw new Error(data.error || 'Failed to plan route');
        }

        // Display the route
        displayRoute(data.route_coords, data.visiting_order, data.total_distance, data.road_segments);

        showStatus('Route planned successfully!', 'success');

    } catch (error) {
        console.error('Error planning route:', error);
        showStatus(`Error: ${error.message}`, 'error');
    } finally {
        planBtn.disabled = false;
        planBtn.textContent = '🚀 Plan Route';
    }
}

// Display the route on the map
function displayRoute(routeCoords, visitingOrder, totalDistance, roadSegments) {
    // Clear existing route
    clearRoute();

    // Create a layer group to hold all route polylines
    routeLayer = L.layerGroup().addTo(map);

    // Draw road segments if available, otherwise draw straight lines
    if (roadSegments && roadSegments.length > 0) {
        // Draw each OSRM road segment
        roadSegments.forEach(segment => {
            const polyline = L.polyline(segment, {
                color: '#667eea',
                weight: 5,
                opacity: 0.8,
                smoothFactor: 1
            });
            routeLayer.addLayer(polyline);
        });
    } else {
        // Fallback: draw straight lines between spots
        const polylineCoords = routeCoords.map(coord => [coord[0], coord[1]]);
        const polyline = L.polyline(polylineCoords, {
            color: '#667eea',
            weight: 5,
            opacity: 0.8,
            smoothFactor: 1
        });
        routeLayer.addLayer(polyline);
    }

    // Add numbered markers for the route
    visitingOrder.forEach((index, position) => {
        const marker = markers[index];
        if (marker) {
            // Create a numbered icon
            const icon = L.divIcon({
                className: 'route-number',
                html: `<div style="background: #667eea; color: white; border-radius: 50%; width: 30px; height: 30px; display: flex; align-items: center; justify-content: center; font-weight: bold; border: 3px solid white; box-shadow: 0 2px 8px rgba(0,0,0,0.3);">${position + 1}</div>`,
                iconSize: [30, 30],
                iconAnchor: [15, 15]
            });
            
            L.marker([marker.lat, marker.lng], { icon: icon }).addTo(map);
        }
    });

    // Fit map to show entire route
    if (routeCoords.length > 0) {
        // Use road segments if available for bounds, otherwise use routeCoords
        const boundsCoords = roadSegments && roadSegments.length > 0
            ? roadSegments.flat()
            : routeCoords.map(coord => [coord[0], coord[1]]);
        const bounds = L.latLngBounds(boundsCoords);
        map.fitBounds(bounds, { padding: [50, 50] });
    }

    // Display route info in sidebar
    const routeInfo = document.getElementById('routeInfo');
    routeInfo.querySelector('.distance').textContent = `Total Distance: ${totalDistance} km`;
    
    const orderList = visitingOrder.map((index, pos) => 
        `<li>Spot ${pos + 1}: ${markers[index].lat.toFixed(4)}, ${markers[index].lng.toFixed(4)}</li>`
    ).join('');
    
    routeInfo.querySelector('.route-order').innerHTML = `<ol>${orderList}</ol>`;
    routeInfo.classList.add('show');
}

// Add custom CSS for route numbers
const style = document.createElement('style');
style.textContent = `
    .route-number {
        background: transparent !important;
        border: none !important;
    }
`;
document.head.appendChild(style);

// Initialize map when page loads
window.addEventListener('load', initMap);
