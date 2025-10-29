import { useState, useEffect } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Button } from '@/components/ui/button'
import { Search, MapPin, Zap, Clock, Filter, Map, List, Star } from 'lucide-react'
import MapView from '@/components/partialViews/MapView'

const FindStations = () => {
  const [searchQuery, setSearchQuery] = useState('')
  const [selectedFilter, setSelectedFilter] = useState('all')
  const [viewMode, setViewMode] = useState('list') // 'list' or 'map'
  const [selectedStation, setSelectedStation] = useState(null)
  const [isLoading, setIsLoading] = useState(true)

  // Comprehensive station data combining both FindChargers and Stations data
  const stations = [
    {
      id: 1,
      name: "Marina Bay Station",
      location: "Marina Bay, CA",
      coordinates: { latitude: 45.9636, longitude: -66.6431 },
      distance: "0.8 miles",
      availableChargers: 3,
      totalChargers: 6,
      chargerTypes: ["Level 2 - 240V", "DC Fast Charge"],
      pricing: "$0.25/kWh",
      amenities: ["WiFi", "Restrooms", "Restaurant"],
      rating: 4.8,
      status: "available"
    },
    {
      id: 2,
      name: "Harbor Point Station",
      location: "Harbor Point, CA",
      coordinates: { latitude: 45.9656, longitude: -66.6451 },
      distance: "1.2 miles",
      availableChargers: 2,
      totalChargers: 4,
      chargerTypes: ["Level 2 - 240V"],
      pricing: "$0.22/kWh",
      amenities: ["WiFi", "Convenience Store"],
      rating: 4.6,
      status: "available"
    },
    {
      id: 3,
      name: "Sunset Marina",
      location: "Sunset Bay, CA",
      coordinates: { latitude: 45.9616, longitude: -66.6411 },
      distance: "2.1 miles",
      availableChargers: 0,
      totalChargers: 3,
      chargerTypes: ["Level 2 - 240V", "Level 1 - 120V"],
      pricing: "$0.20/kWh",
      amenities: ["WiFi", "Restrooms"],
      rating: 4.2,
      status: "busy"
    },
    {
      id: 4,
      name: "Downtown Marina",
      location: "Downtown Marina, CA",
      coordinates: { latitude: 45.9676, longitude: -66.6471 },
      distance: "2.8 miles",
      availableChargers: 4,
      totalChargers: 8,
      chargerTypes: ["Level 2 - 240V", "DC Fast Charge", "CHAdeMO"],
      pricing: "$0.28/kWh",
      amenities: ["WiFi", "Restrooms", "Restaurant", "Shopping"],
      rating: 4.9,
      status: "available"
    },
    {
      id: 5,
      name: "Coastal Power Hub",
      location: "Coastal Drive, CA",
      coordinates: { latitude: 45.9596, longitude: -66.6391 },
      distance: "3.5 miles",
      availableChargers: 6,
      totalChargers: 10,
      chargerTypes: ["DC Fast Charge", "Level 2 - 240V"],
      pricing: "$0.30/kWh",
      amenities: ["WiFi", "Restrooms", "Food Court", "EV Service"],
      rating: 4.7,
      status: "available"
    }
  ]

  useEffect(() => {
    // Simulate loading time
    const timer = setTimeout(() => {
      setIsLoading(false)
    }, 1000)
    return () => clearTimeout(timer)
  }, [])

  // Filter stations based on search query and selected filter
  const filteredStations = stations.filter(station => {
    // Search filter
    if (searchQuery) {
      const query = searchQuery.toLowerCase()
      if (!station.name.toLowerCase().includes(query) && 
          !station.location.toLowerCase().includes(query)) {
        return false
      }
    }

    // Status filter
    if (selectedFilter === 'available' && station.status !== 'available') {
      return false
    }

    // Fast charging filter
    if (selectedFilter === 'fast-charge' && 
        !station.chargerTypes.some(type => type.includes('DC Fast') || type.includes('CHAdeMO'))) {
      return false
    }

    return true
  })

  const getStatusColor = (status) => {
    return status === 'available' 
      ? 'bg-green-100 text-green-800' 
      : 'bg-red-100 text-red-800'
  }

  const handleStationSelect = (stationId) => {
    const station = stations.find(s => s.id.toString() === stationId)
    setSelectedStation(station)
  }

  const handleStationDeselect = () => {
    setSelectedStation(null)
  }

  const handleLocationSelect = (coordinates) => {
    // Handle location selection on map
    console.log('Location selected:', coordinates)
  }

  const handleFilterChange = (newFilters) => {
    // Handle filter changes from map component
    console.log('Filters changed:', newFilters)
  }

  const handleReserve = (stationId) => {
    // Handle reservation
    console.log('Reserve station:', stationId)
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-screen bg-background">
        <div className="text-center space-y-3">
          <div className="inline-block h-8 w-8 animate-spin rounded-full border-4 border-solid border-primary border-r-transparent"></div>
          <p className="text-sm text-muted-foreground">Loading stations...</p>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold text-gray-900">Find Charging Stations</h1>
        <p className="text-gray-600 mt-2">
          Discover and book charging stations near you
        </p>
      </div>

      {/* Search and Filters */}
      <Card>
        <CardContent>
          <div className="flex flex-col md:flex-row gap-4 items-center">
            <div className="relative flex-1">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 h-4 w-4" />
              <Input
                placeholder="Search by station name or location..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="pl-10"
              />
            </div>
            <div className="flex gap-2">
              <button
                onClick={() => setSelectedFilter('all')}
                className={`px-4 py-2 rounded-md text-sm font-medium transition-colors ${
                  selectedFilter === 'all' 
                    ? 'bg-blue-600 text-white' 
                    : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                }`}
              >
                All Stations
              </button>
              <button
                onClick={() => setSelectedFilter('available')}
                className={`px-4 py-2 rounded-md text-sm font-medium transition-colors ${
                  selectedFilter === 'available' 
                    ? 'bg-blue-600 text-white' 
                    : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                }`}
              >
                Available Now
              </button>
              <button
                onClick={() => setSelectedFilter('fast-charge')}
                className={`px-4 py-2 rounded-md text-sm font-medium transition-colors ${
                  selectedFilter === 'fast-charge' 
                    ? 'bg-blue-600 text-white' 
                    : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                }`}
              >
                Fast Charging
              </button>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* View Toggle and Results Count */}
      <div className="flex items-center justify-between">
        <div className="text-sm text-gray-600">
          Showing {filteredStations.length} charging station{filteredStations.length !== 1 ? 's' : ''}
        </div>
        <div className="flex gap-2">
          <Button
            variant={viewMode === 'list' ? 'default' : 'outline'}
            size="sm"
            onClick={() => setViewMode('list')}
            className="flex items-center gap-2"
          >
            <List className="h-4 w-4" />
            List View
          </Button>
          <Button
            variant={viewMode === 'map' ? 'default' : 'outline'}
            size="sm"
            onClick={() => setViewMode('map')}
            className="flex items-center gap-2"
          >
            <Map className="h-4 w-4" />
            Map View
          </Button>
        </div>
      </div>

      {/* Content Area */}
      {viewMode === 'map' ? (
        <div className="h-screen w-full overflow-hidden rounded-lg border">
          <MapView
            stations={filteredStations.map(station => ({
              id: station.id.toString(),
              name: station.name,
              location: station.coordinates,
              chargerTypes: station.chargerTypes,
              totalChargers: station.totalChargers,
              availableChargers: station.availableChargers,
              status: station.status === 'available' ? 'active' : 'maintenance'
            }))}
            filters={{
              availableOnly: selectedFilter === 'available',
              chargerTypes: selectedFilter === 'fast-charge' ? ['DC Fast Charge', 'CHAdeMO'] : [],
              maxDistance: null
            }}
            selectedStation={selectedStation}
            onStationSelect={handleStationSelect}
            onStationDeselect={handleStationDeselect}
            onLocationSelect={handleLocationSelect}
            onFilterChange={handleFilterChange}
            onReserve={handleReserve}
          />
        </div>
      ) : (
        /* List View */
        <div className="space-y-4">
          {filteredStations.map((station) => (
            <Card key={station.id} className="hover:shadow-lg transition-shadow">
              <CardContent className="pt-6">
                <div className="flex items-start justify-between">
                  <div className="space-y-3 flex-1">
                    <div className="flex items-start justify-between">
                      <div>
                        <h3 className="text-xl font-semibold">{station.name}</h3>
                        <div className="flex items-center space-x-2 text-gray-600 mt-1">
                          <MapPin className="h-4 w-4" />
                          <span>{station.location}</span>
                          <span>•</span>
                          <span>{station.distance}</span>
                        </div>
                      </div>
                      <span className={`px-3 py-1 rounded-full text-sm font-medium ${getStatusColor(station.status)}`}>
                        {station.status === 'available' ? 'Available' : 'Busy'}
                      </span>
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                      <div>
                        <p className="text-sm font-medium text-gray-900">Availability</p>
                        <div className="flex items-center space-x-2">
                          <Zap className="h-4 w-4 text-green-600" />
                          <span className="text-sm text-gray-600">
                            {station.availableChargers} of {station.totalChargers} chargers available
                          </span>
                        </div>
                      </div>
                      <div>
                        <p className="text-sm font-medium text-gray-900">Charger Types</p>
                        <p className="text-sm text-gray-600">
                          {station.chargerTypes.join(', ')}
                        </p>
                      </div>
                      <div>
                        <p className="text-sm font-medium text-gray-900">Pricing</p>
                        <p className="text-sm text-gray-600">{station.pricing}</p>
                      </div>
                    </div>

                    <div>
                      <p className="text-sm font-medium text-gray-900 mb-1">Amenities</p>
                      <div className="flex flex-wrap gap-2">
                        {station.amenities.map((amenity, index) => (
                          <span key={index} className="px-2 py-1 bg-gray-100 text-gray-700 rounded-md text-xs">
                            {amenity}
                          </span>
                        ))}
                      </div>
                    </div>

                    <div className="flex items-center justify-between">
                      <div className="flex items-center space-x-1">
                        <Star className="h-4 w-4 text-yellow-500 fill-current" />
                        <span className="text-sm font-medium">{station.rating}</span>
                        <span className="text-sm text-gray-600">rating</span>
                      </div>
                      <div className="flex space-x-2">
                        <Button 
                          variant="outline" 
                          size="sm"
                          onClick={() => handleStationSelect(station.id.toString())}
                        >
                          View Details
                        </Button>
                        <Button 
                          size="sm"
                          disabled={station.status !== 'available'}
                          onClick={() => handleReserve(station.id)}
                        >
                          {station.status === 'available' ? 'Book Now' : 'Not Available'}
                        </Button>
                      </div>
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  )
}

export default FindStations