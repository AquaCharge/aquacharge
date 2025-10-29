import { useState } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Search, MapPin, Zap, Clock, Filter } from 'lucide-react'

const FindChargers = () => {
  const [searchQuery, setSearchQuery] = useState('')
  const [selectedFilter, setSelectedFilter] = useState('all')

  // Mock charger stations data
  const stations = [
    {
      id: 1,
      name: "Marina Bay Station",
      location: "Marina Bay, CA",
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
      name: "North Harbor Station",
      location: "North Harbor, CA",
      distance: "3.5 miles",
      availableChargers: 4,
      totalChargers: 8,
      chargerTypes: ["Level 2 - 240V", "DC Fast Charge", "Level 1 - 120V"],
      pricing: "$0.28/kWh",
      amenities: ["WiFi", "Restrooms", "Restaurant", "Fuel Dock"],
      rating: 4.9,
      status: "available"
    }
  ]

  const getStatusColor = (status) => {
    switch (status) {
      case 'available':
        return 'bg-green-100 text-green-800'
      case 'busy':
        return 'bg-red-100 text-red-800'
      default:
        return 'bg-gray-100 text-gray-800'
    }
  }

  const filteredStations = stations.filter(station => {
    const matchesSearch = station.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
                         station.location.toLowerCase().includes(searchQuery.toLowerCase())
    
    if (selectedFilter === 'all') return matchesSearch
    if (selectedFilter === 'available') return matchesSearch && station.status === 'available'
    if (selectedFilter === 'fast-charge') return matchesSearch && station.chargerTypes.includes('DC Fast Charge')
    
    return matchesSearch
  })

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-gray-900">Find Charging Stations</h1>
        <p className="text-gray-600 mt-2">Locate and book charging stations near you</p>
      </div>

      {/* Search and Filters */}
      <Card>
        <CardContent className="pt-6">
          <div className="flex flex-col md:flex-row gap-4">
            <div className="flex-1 relative">
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

      {/* Results Count */}
      <div className="text-sm text-gray-600">
        Showing {filteredStations.length} charging station{filteredStations.length !== 1 ? 's' : ''}
      </div>

      {/* Station List */}
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
                      <p className="text-sm text-gray-600">
                        {station.availableChargers} of {station.totalChargers} chargers available
                      </p>
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
                      <span className="text-yellow-500">★</span>
                      <span className="text-sm font-medium">{station.rating}</span>
                      <span className="text-sm text-gray-600">rating</span>
                    </div>
                    <div className="flex space-x-2">
                      <button className="px-4 py-2 border border-gray-300 rounded-md text-sm font-medium hover:bg-gray-50 transition-colors">
                        View Details
                      </button>
                      <button 
                        className={`px-4 py-2 rounded-md text-sm font-medium transition-colors ${
                          station.status === 'available'
                            ? 'bg-blue-600 text-white hover:bg-blue-700'
                            : 'bg-gray-300 text-gray-500 cursor-not-allowed'
                        }`}
                        disabled={station.status !== 'available'}
                      >
                        {station.status === 'available' ? 'Book Now' : 'Not Available'}
                      </button>
                    </div>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  )
}

export default FindChargers