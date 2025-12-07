// static/js/main.js

document.addEventListener('DOMContentLoaded', function() {
    const mapElement = document.getElementById('map');

    if (mapElement) {
        // Hanya inisialisasi peta jika elemen dengan ID 'map' ada di halaman
        initCCTVMap();
    }
    
    // Inisialisasi Lucide icons (jika digunakan di halaman lain yang memanggil main.js)
    if (typeof lucide !== 'undefined') {
        lucide.createIcons();
    }
});


function initCCTVMap() {
    // Koordinat tengah Jawa Tengah (perkiraan)
    const centralJavaCoords = [-7.3000, 110.0000]; // Contoh: Magelang atau Salatiga area
    const initialZoom = 9; // Zoom level yang sesuai untuk melihat sebagian besar Jateng

    // Inisialisasi peta Leaflet
    const map = L.map('map').setView(centralJavaCoords, initialZoom);

    // Tambahkan layer peta OpenStreetMap
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
    }).addTo(map);

    // Fetch CCTV locations from Flask API
    fetch('/api/cctv_locations')
        .then(response => {
            if (!response.ok) {
                throw new Error('Network response was not ok ' + response.statusText);
            }
            return response.json();
        })
        .then(cctvLocations => {
            cctvLocations.forEach(cctv => {
                let iconUrl = cctv.status === "Aktif" ?
                              'https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-2x-green.png' :
                              'https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-2x-red.png';

                let shadowUrl = 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/0.7.7/images/marker-shadow.png';

                let cctvIcon = new L.Icon({
                    iconUrl: iconUrl,
                    shadowUrl: shadowUrl,
                    iconSize: [25, 41],
                    iconAnchor: [12, 41],
                    popupAnchor: [1, -34],
                    shadowSize: [41, 41]
                });

                L.marker([cctv.lat, cctv.lon], {icon: cctvIcon})
                    .addTo(map)
                    .bindPopup(`<b>${cctv.name}</b><br>Status: ${cctv.status}<br>Update: ${cctv.last_update}`);
            });
        })
        .catch(error => {
            console.error('There has been a problem with your fetch operation:', error);
            // Optionally add a fallback message to the map area
            const mapContainer = document.getElementById('map');
            if (mapContainer) {
                mapContainer.innerHTML = '<div style="text-align: center; padding-top: 50px; color: gray;">Gagal memuat data CCTV. Silakan coba lagi nanti.</div>';
            }
        });
}