'use client';

import { useEffect, useRef } from 'react';
import 'leaflet/dist/leaflet.css';

export default function CrimeMap({ cases, onCaseSelected }) {
  const container = useRef(null);
  const map = useRef(null);
  const markers = useRef(null);

  useEffect(() => {
    let active = true;
    async function draw() {
      const L = (await import('leaflet')).default;
      if (!active || !container.current) return;
      if (!map.current) {
        map.current = L.map(container.current).setView([15.2, 75.9], 7);
        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
          attribution: '© OpenStreetMap contributors', maxZoom: 18,
        }).addTo(map.current);
        markers.current = L.layerGroup().addTo(map.current);
      }
      markers.current.clearLayers();
      const bounds = [];
      cases.forEach((item) => {
        if (!item.latitude || !item.longitude) return;
        const marker = L.circleMarker([item.latitude, item.longitude], {
          radius: 4, color: '#8c82ff', fillColor: '#a79fff', fillOpacity: 0.65, weight: 1,
        }).bindTooltip(`${item.CrimeNo} · ${item.CrimeType}`);
        marker.on('click', () => onCaseSelected(item));
        markers.current.addLayer(marker);
        bounds.push([item.latitude, item.longitude]);
      });
      if (bounds.length) map.current.fitBounds(bounds, { padding: [24, 24], maxZoom: 11 });
      map.current.invalidateSize();
    }
    draw();
    return () => { active = false; };
  }, [cases, onCaseSelected]);

  return <div className="leaflet-canvas" ref={container} aria-label="Geocoded FIR map" />;
}
