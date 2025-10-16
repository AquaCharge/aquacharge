import React, { useState, useEffect } from 'react';
import MapView from '@/components/partialViews/MapView';

const Stations = () => {
  const [stations, setStations] = useState([]);
  const [selectedStation, setSelectedStation] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [filters, setFilters] = useState({
    availableOnly: false,
    chargerTypes: [],
    maxDistance: null
  });

  // Mock charging station data - Replace with API call
  const mockStations = [
    {
      id: '1',
      name: 'Harbour Esport Hub',
      location: { latitude: 45.9636, longitude: -66.6431 },
      chargerTypes: ['Type 2', 'CCS'],
      totalChargers: 4,
      availableChargers: 2,
      status: 'active'
    },
    {
      id: '2',
      name: 'City Center Lot',
      location: { latitude: 45.9656, longitude: -66.6451 },
      chargerTypes: ['Type 2', 'CHAdeMO'],
      totalChargers: 6,
      availableChargers: 5,
      status: 'active'
    },
    {
      id: '3',
      name: 'Waterfront Station',
      location: { latitude: 45.9616, longitude: -66.6411 },
      chargerTypes: ['Type 2'],
      totalChargers: 3,
      availableChargers: 0,
      status: 'active'
    },
    {
      id: '4',
      name: 'Downtown Marina',
      location: { latitude: 45.9676, longitude: -66.6471 },
      chargerTypes: ['Type 2', 'CCS', 'CHAdeMO'],
      totalChargers: 8,
      availableChargers: 8,
      status: 'maintenance'
    }
  ];

  useEffect(() => {
    // Simulate API call
    // TODO: Replace with actual API call to Flask backend
    // fetch('/api/charging-stations')
    //   .then(res => res.json())
    //   .then(data => {
    //     setStations(data);
    //     setIsLoading(false);
    //   })
    //   .catch(error => {
    //     console.error('Error fetching stations:', error);
    //     setIsLoading(false);
    //   });

    // For now, use mock data
    setTimeout(() => {
      setStations(mockStations);
      setIsLoading(false);
    }, 500);
  }, []);

  const handleStationSelect = (station) => {
    setSelectedStation(station);
  };

  const handleStationDeselect = () => {
    setSelectedStation(null);
  };

  const handleLocationSelect = (location) => {
    // Handle when a location (not a station) is selected from search
    console.log('Location selected:', location);
    // Map will already be panned, but you could do additional things here
  };

  const handleReserve = (station) => {
    console.log('Reserving station:', station.id);
    // TODO: Navigate to booking page or open reservation modal
    // navigate(`/bookings/new?stationId=${station.id}`);
  };

  const handleFilterChange = (newFilters) => {
    setFilters(newFilters);
    // Filtering logic will be applied when rendering or can filter here
    console.log('Filters updated:', newFilters);
  };

  // Apply filters to stations
  const filteredStations = stations.filter(station => {
    // Available only filter
    if (filters.availableOnly && station.availableChargers === 0) {
      return false;
    }

    // Charger type filter
    if (filters.chargerTypes.length > 0) {
      const hasMatchingCharger = filters.chargerTypes.some(type =>
        station.chargerTypes.includes(type)
      );
      if (!hasMatchingCharger) {
        return false;
      }
    }

    // Distance filter would go here (requires user location)
    // if (filters.maxDistance !== null) {
    //   const distance = calculateDistance(userLocation, station.location);
    //   if (distance > filters.maxDistance) {
    //     return false;
    //   }
    // }

    return true;
  });

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-screen bg-background">
        <div className="text-center space-y-3">
          <div className="inline-block h-8 w-8 animate-spin rounded-full border-4 border-solid border-primary border-r-transparent"></div>
          <p className="text-sm text-muted-foreground">Loading stations...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="h-screen w-full overflow-hidden">
      <MapView
        stations={filteredStations}
        filters={filters}
        selectedStation={selectedStation}
        onStationSelect={handleStationSelect}
        onStationDeselect={handleStationDeselect}
        onLocationSelect={handleLocationSelect}
        onFilterChange={handleFilterChange}
        onReserve={handleReserve}
      />
    </div>
  );
};

export default Stations;