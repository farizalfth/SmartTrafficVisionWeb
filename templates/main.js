document.addEventListener('DOMContentLoaded', () => {
  const map = L.map('map').setView([-6.8797, 109.1256], 13);

  L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    attribution: '&copy; OpenStreetMap contributors',
    maxZoom: 19
  }).addTo(map);

  L.marker([-6.8797, 109.1256])
    .addTo(map)
    .bindPopup('<b>Smart Traffic Vision</b><br>Contoh lokasi utama pemantauan.')
    .openPopup();
});
