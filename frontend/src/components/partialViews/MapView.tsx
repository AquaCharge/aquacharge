import React, { useEffect, useRef } from 'react';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import StationDetailsCard from '@/components/station/StationDetailsCard';
import StationSearchFilters from '@/components/station/StationSearchFilters';

const MapView = ({ 
  stations = [],
  filters = {
    availableOnly: false,
    chargerTypes: [],
    maxDistance: null
  },
  selectedStation = null, 
  onStationSelect = () => {}, 
  onStationDeselect = () => {},
  onLocationSelect = () => {},
  onFilterChange = () => {},
  onReserve = () => {}
}) => {
  const mapRef = useRef(null);
  const mapInstanceRef = useRef(null);
  const markersRef = useRef([]);

  const getStatusColor = (station) => {
    if (station.status !== 'active') return '#94a3b8';
    if (station.availableChargers === 0) return '#ef4444';
    if (station.availableChargers <= 2) return '#f59e0b';
    return '#10b981';
  };

  const createCustomIcon = (station) => {
    const color = getStatusColor(station);
    return L.divIcon({
      className: 'custom-marker',
      html: `
        <div style="
          background-color: ${color};
          width: 40px;
          height: 40px;
          border-radius: 50% 50% 50% 0;
          transform: rotate(-45deg);
          border: 2px solid white;
          box-shadow: 0 2px 8px rgba(0,0,0,0.3);
          display: flex;
          align-items: center;
          justify-content: center;
          cursor: pointer;
          transition: all 0.2s ease;
        ">
          <span style="
            transform: rotate(45deg);
            color: white;
            font-weight: bold;
            font-size: 14px;
          ">${station.availableChargers}</span>
        </div>
      `,
      iconSize: [40, 40],
      iconAnchor: [20, 40],
      popupAnchor: [0, -40]
    });
  };

  const handleSearchStationSelect = (station) => {
    onStationSelect(station);
    // Pan and zoom to station
    mapInstanceRef.current?.setView(
      [station.location.latitude, station.location.longitude],
      15,
      { animate: true }
    );
  };

  const handleSearchLocationSelect = (location) => {
    onLocationSelect(location);
    // Pan and zoom to location
    mapInstanceRef.current?.setView(
      [location.lat, location.lon],
      15,
      { animate: true }
    );
  };

  // Initialize map once
  useEffect(() => {
    if (mapInstanceRef.current) return;

    // Initialize map
    mapInstanceRef.current = L.map(mapRef.current).setView([45.9636, -66.6431], 13);

    // Add tile layer
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
      maxZoom: 19
    }).addTo(mapInstanceRef.current);

    return () => {
      if (mapInstanceRef.current) {
        mapInstanceRef.current.remove();
        mapInstanceRef.current = null;
      }
    };
  }, []);

  // Update markers when stations change
  useEffect(() => {
    if (!mapInstanceRef.current) return;

    // Clear existing markers
    markersRef.current.forEach(marker => marker.remove());
    markersRef.current = [];

    // Add new markers
    stations.forEach(station => {
      const marker = L.marker(
        [station.location.latitude, station.location.longitude],
        { icon: createCustomIcon(station) }
      ).addTo(mapInstanceRef.current);

      marker.on('click', () => {
        onStationSelect(station);
      });

      markersRef.current.push(marker);
    });

    return () => {
      markersRef.current.forEach(marker => marker.remove());
      markersRef.current = [];
    };
  }, [stations, onStationSelect]);

  return (
    <div className="flex flex-col h-screen">
      {/* Map Container */}
      <div className="relative flex-1">
        <div ref={mapRef} className="w-full h-full" />

        {/* Station Details Card */}
        {selectedStation && (
          <div className="absolute bottom-8 left-1/2 transform -translate-x-1/2 w-full max-w-md px-4 z-[1000] animate-in slide-in-from-bottom-4 duration-300">
            <StationDetailsCard
              station={selectedStation}
              onClose={onStationDeselect}
              onReserve={onReserve}
            />
          </div>
        )}
      </div>
    </div>
  );
};

export default MapView;