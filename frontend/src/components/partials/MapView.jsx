import React, { useEffect, useRef, useState } from 'react';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { X, Search, Filter } from 'lucide-react';

const MapView = () => {
  const mapRef = useRef(null);
  const mapInstanceRef = useRef(null);
  const markersRef = useRef([]);
  const [selectedStation, setSelectedStation] = useState(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState([]);
  const [showResults, setShowResults] = useState(false);
  const [isSearching, setIsSearching] = useState(false);

  // Mock charging station data
  const chargingStations = [
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

  const handleSearch = async (query) => {
    setSearchQuery(query);
    
    if (!query.trim()) {
      setSearchResults([]);
      setShowResults(false);
      return;
    }

    setIsSearching(true);
    setShowResults(true);

    // Search in charging stations
    const stationResults = chargingStations.filter(station =>
      station.name.toLowerCase().includes(query.toLowerCase())
    );

    // Search for locations using Nominatim (OpenStreetMap geocoding)
    try {
      const response = await fetch(
        `https://nominatim.openstreetmap.org/search?format=json&q=${encodeURIComponent(query)}&limit=5`
      );
      const locationResults = await response.json();

      const combinedResults = [
        ...stationResults.map(station => ({
          type: 'station',
          data: station,
          display: station.name,
          subtitle: `${station.availableChargers} available`
        })),
        ...locationResults.map(loc => ({
          type: 'location',
          data: loc,
          display: loc.display_name,
          subtitle: 'Location'
        }))
      ];

      setSearchResults(combinedResults);
    } catch (error) {
      console.error('Search error:', error);
      setSearchResults(stationResults.map(station => ({
        type: 'station',
        data: station,
        display: station.name,
        subtitle: `${station.availableChargers} available`
      })));
    }

    setIsSearching(false);
  };

  const handleResultClick = (result) => {
    if (result.type === 'station') {
      const station = result.data;
      setSelectedStation(station);
      mapInstanceRef.current?.setView(
        [station.location.latitude, station.location.longitude],
        15,
        { animate: true }
      );
    } else {
      const location = result.data;
      mapInstanceRef.current?.setView(
        [parseFloat(location.lat), parseFloat(location.lon)],
        15,
        { animate: true }
      );
    }
    setShowResults(false);
    setSearchQuery('');
  };

  const clearSearch = () => {
    setSearchQuery('');
    setSearchResults([]);
    setShowResults(false);
  };

  useEffect(() => {
    if (mapInstanceRef.current) return;

    // Initialize map
    mapInstanceRef.current = L.map(mapRef.current).setView([45.9636, -66.6431], 13);

    // Add tile layer
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
      maxZoom: 19
    }).addTo(mapInstanceRef.current);

    // Add markers for charging stations
    chargingStations.forEach(station => {
      const marker = L.marker(
        [station.location.latitude, station.location.longitude],
        { icon: createCustomIcon(station) }
      ).addTo(mapInstanceRef.current);

      marker.on('click', () => {
        setSelectedStation(station);
      });

      markersRef.current.push(marker);
    });

    return () => {
      markersRef.current.forEach(marker => marker.remove());
      markersRef.current = [];
      if (mapInstanceRef.current) {
        mapInstanceRef.current.remove();
        mapInstanceRef.current = null;
      }
    };
  }, []);

  const getAvailabilityStatus = () => {
    if (selectedStation.status !== 'active') return 'Under Maintenance';
    if (selectedStation.availableChargers === 0) return 'Fully Occupied';
    if (selectedStation.availableChargers === selectedStation.totalChargers) return 'All Available';
    return 'Limited Availability';
  };

  return (
    <div className="flex flex-col h-screen">
      {/* Search and Filter Bar */}
      <div className="bg-background border-b py-3 space-y-3">
        <div className="flex gap-2">
          {/* Search Bar */}
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
            <Input
              type="text"
              placeholder="Search stations or locations..."
              value={searchQuery}
              onChange={(e) => handleSearch(e.target.value)}
              className="pl-10 pr-10"
            />
            {searchQuery && (
              <Button
                variant="ghost"
                size="icon"
                className="absolute right-1 top-1/2 transform -translate-y-1/2 h-7 w-7"
                onClick={clearSearch}
              >
                <X className="h-4 w-4" />
              </Button>
            )}

            {/* Search Results Dropdown */}
            {showResults && searchResults.length > 0 && (
              <Card className="absolute top-full mt-2 w-full shadow-xl border z-3000 max-h-80 overflow-y-auto">
                <CardContent className="p-0">
                  {searchResults.map((result, index) => (
                    <button
                      key={index}
                      onClick={() => handleResultClick(result)}
                      className="w-full px-4 py-3 text-left hover:bg-accent transition-colors border-b last:border-b-0 flex items-start gap-3"
                    >
                      <div className="flex-1 min-w-0">
                        <p className="font-medium text-sm truncate">{result.display}</p>
                        <p className="text-xs text-muted-foreground truncate">{result.subtitle}</p>
                      </div>
                      {result.type === 'station' && (
                        <Badge variant="outline" className="text-xs shrink-0">
                          Station
                        </Badge>
                      )}
                    </button>
                  ))}
                </CardContent>
              </Card>
            )}

            {showResults && searchResults.length === 0 && !isSearching && searchQuery && (
              <Card className="absolute top-full mt-2 w-full shadow-xl border z-50">
                <CardContent className="p-4">
                  <p className="text-sm text-muted-foreground text-center">No results found</p>
                </CardContent>
              </Card>
            )}
          </div>

          {/* Filter Button */}
          <Button variant="outline" size="icon">
            <Filter className="h-4 w-4" />
          </Button>
        </div>
      </div>

      {/* Map Container */}
      <div className="relative flex-1">
        <div ref={mapRef} className="w-full h-full" />

        {/* Station Details Card */}
        {selectedStation && (
          <div className="absolute bottom-8 left-1/2 transform -translate-x-1/2 w-full max-w-md px-4 z-[1000] animate-in slide-in-from-bottom-4 duration-300">
            <Card className="border-0 shadow-xl">
              <CardHeader className="space-y-3 pb-4">
                <div className="flex items-start justify-between">
                  <div className="space-y-1 flex-1">
                    <CardTitle className="text-xl font-semibold leading-tight">
                      {selectedStation.name}
                    </CardTitle>
                    <p className="text-sm text-muted-foreground">
                      {getAvailabilityStatus()}
                    </p>
                  </div>
                  <Button
                    variant="ghost"
                    size="icon"
                    className="h-8 w-8 -mt-1 -mr-2"
                    onClick={() => setSelectedStation(null)}
                  >
                    <X className="h-4 w-4" />
                  </Button>
                </div>
              </CardHeader>

              <CardContent className="space-y-6 pt-0">
                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-1">
                    <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
                      Available
                    </p>
                    <p className="text-2xl font-bold">
                      {selectedStation.availableChargers}
                      <span className="text-base font-normal text-muted-foreground ml-1">
                        of {selectedStation.totalChargers}
                      </span>
                    </p>
                  </div>
                  
                  <div className="space-y-1">
                    <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
                      Status
                    </p>
                    <Badge 
                      variant={selectedStation.status === 'active' ? 'default' : 'secondary'}
                      className="text-xs font-medium"
                    >
                      {selectedStation.status}
                    </Badge>
                  </div>
                </div>

                <div className="space-y-2">
                  <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
                    Charger Types
                  </p>
                  <div className="flex flex-wrap gap-2">
                    {selectedStation.chargerTypes.map((type, index) => (
                      <span
                        key={index}
                        className="px-3 py-1 text-sm font-medium bg-secondary text-secondary-foreground rounded-md"
                      >
                        {type}
                      </span>
                    ))}
                  </div>
                </div>

                <Button 
                  className="w-full h-11 font-medium"
                  disabled={selectedStation.availableChargers === 0 || selectedStation.status !== 'active'}
                >
                  Reserve Charging Slot
                </Button>
              </CardContent>
            </Card>
          </div>
        )}
      </div>
    </div>
  );
};

export default MapView;