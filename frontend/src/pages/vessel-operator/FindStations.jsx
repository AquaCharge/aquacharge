import { useState, useEffect, useMemo } from 'react'
import { Card, CardContent } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Button } from '@/components/ui/button'
import { Search, MapPin, Zap, Map, List, Star } from 'lucide-react'
import MapView from '@/components/partialViews/MapView'
import { getApiEndpoint } from '@/config/api'

// Backend StationStatus: 1=ACTIVE, 2=MAINTENANCE, 3=INACTIVE. Charger status same.
const STATION_STATUS_ACTIVE = 1

/** Build view-model stations from API stations + chargers (group chargers by station). */
function buildStationsView(stationsPayload, chargersPayload) {
  const chargersByStation = (chargersPayload || []).reduce((acc, c) => {
    const sid = c.chargingStationId
    if (!sid) return acc
    if (!acc[sid]) acc[sid] = []
    acc[sid].push(c)
    return acc
  }, {})

  return (stationsPayload || []).map((s) => {
    const id = s.id
    const chargers = chargersByStation[id] || []
    const activeCount = chargers.filter((c) => Number(c.status) === STATION_STATUS_ACTIVE).length
    const stationActive = Number(s.status) === STATION_STATUS_ACTIVE
    const lat = typeof s.latitude === 'number' ? s.latitude : Number(s.latitude)
    const lng = typeof s.longitude === 'number' ? s.longitude : Number(s.longitude)
    const locationParts = [s.city, s.provinceOrState, s.country].filter(Boolean)
    const locationStr = locationParts.length ? locationParts.join(', ') : '—'
    const chargerTypes = [...new Set(chargers.map((c) => c.chargerType).filter(Boolean))]

    return {
      id,
      name: s.displayName || 'Unnamed Station',
      location: locationStr,
      coordinates: { latitude: lat, longitude: lng },
      distance: null,
      availableChargers: stationActive ? activeCount : 0,
      totalChargers: chargers.length,
      chargerTypes: chargerTypes.length ? chargerTypes : ['—'],
      pricing: '—',
      amenities: [],
      rating: null,
      status: stationActive && activeCount > 0 ? 'available' : 'busy'
    }
  })
}

const FindStations = () => {
  const [searchQuery, setSearchQuery] = useState('')
  const [selectedFilter, setSelectedFilter] = useState('all')
  const [viewMode, setViewMode] = useState('list')
  const [selectedStation, setSelectedStation] = useState(null)
  const [expandedStationId, setExpandedStationId] = useState(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState(null)
  const [stationsPayload, setStationsPayload] = useState([])
  const [chargersPayload, setChargersPayload] = useState([])

  const stations = useMemo(
    () => buildStationsView(stationsPayload, chargersPayload),
    [stationsPayload, chargersPayload]
  )

  useEffect(() => {
    let cancelled = false
    const fetchData = async () => {
      setIsLoading(true)
      setError(null)
      try {
        const [stationsRes, chargersRes] = await Promise.all([
          fetch(getApiEndpoint('/api/stations')),
          fetch(getApiEndpoint('/api/chargers'))
        ])
        if (cancelled) return
        if (!stationsRes.ok) throw new Error('Failed to load stations')
        if (!chargersRes.ok) throw new Error('Failed to load chargers')
        const [stationsData, chargersData] = await Promise.all([
          stationsRes.json(),
          chargersRes.json()
        ])
        if (cancelled) return
        setStationsPayload(Array.isArray(stationsData) ? stationsData : [])
        setChargersPayload(Array.isArray(chargersData) ? chargersData : [])
      } catch (e) {
        if (!cancelled) setError(e.message || 'Failed to load data')
      } finally {
        if (!cancelled) setIsLoading(false)
      }
    }
    fetchData()
    return () => { cancelled = true }
  }, [])

  const filteredStations = stations.filter((station) => {
    if (searchQuery) {
      const query = searchQuery.toLowerCase()
      if (
        !station.name.toLowerCase().includes(query) &&
        !station.location.toLowerCase().includes(query)
      ) {
        return false
      }
    }
    if (selectedFilter === 'available' && station.status !== 'available') return false
    if (
      selectedFilter === 'fast-charge' &&
      !station.chargerTypes.some(
        (type) => type && (type.includes('DC Fast') || type.includes('CHAdeMO'))
      )
    ) {
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
    const station = stations.find((s) => String(s.id) === String(stationId))
    setSelectedStation(station)
  }

  const handleStationDeselect = () => {
    setSelectedStation(null)
  }

  const toggleCardExpand = (station) => {
    setExpandedStationId((prev) =>
      String(prev) === String(station.id) ? null : station.id
    )
  }

  const isExpanded = (station) => String(expandedStationId) === String(station.id)

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

  if (error) {
    return (
      <div className="space-y-6">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Find Charging Stations</h1>
          <p className="text-gray-600 mt-2">Discover and book charging stations near you</p>
        </div>
        <Card>
          <CardContent className="pt-6">
            <p className="text-destructive">{error}</p>
          </CardContent>
        </Card>
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
                          <span>{station.location} | {station.coordinates.latitude.toFixed(5)},{' '}
                          {station.coordinates.longitude.toFixed(5)}</span>
                          {station.distance != null && (
                            <>
                              <span>•</span>
                              <span>{station.distance}</span>
                            </>
                          )}
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

                    <div className="flex items-center justify-between">
                      <div className="flex items-center space-x-1">
                        {station.rating != null && (
                          <>
                            <Star className="h-4 w-4 text-yellow-500 fill-current" />
                            <span className="text-sm font-medium">{station.rating}</span>
                            <span className="text-sm text-gray-600">rating</span>
                          </>
                        )}
                      </div>
                      <div className="flex space-x-2">
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => toggleCardExpand(station)}
                        >
                          {isExpanded(station) ? 'Hide Details' : 'View Details'}
                        </Button>
                        <Button
                          size="sm"
                          disabled={station.status !== 'available'}
                          onClick={() => handleReserve(String(station.id))}
                        >
                          {station.status === 'available' ? 'Book Now' : 'Not Available'}
                        </Button>
                      </div>
                    </div>
                  </div>
                </div>

                {/* Expanded: station details + chargers */}
                {isExpanded(station) && (
                  <div className="mt-6 pt-6 border-t border-gray-200 space-y-4">
                    
                    <h4 className="text-sm font-semibold text-gray-900">Chargers</h4>
                    {(() => {
                      const stationChargers = (chargersPayload || []).filter(
                        (c) => String(c.chargingStationId) === String(station.id)
                      )
                      if (stationChargers.length === 0) {
                        return (
                          <p className="text-sm text-gray-500">No chargers at this station.</p>
                        )
                      }
                      return (
                        <div className="overflow-x-auto rounded-md border border-gray-200">
                          <table className="w-full text-sm">
                            <thead>
                              <tr className="border-b border-gray-200 bg-gray-50">
                                <th className="px-4 py-2 text-left font-medium text-gray-900">
                                  Charger type
                                </th>
                                <th className="px-4 py-2 text-left font-medium text-gray-900">
                                  Max rate
                                </th>
                                <th className="px-4 py-2 text-left font-medium text-gray-900">
                                  Status
                                </th>
                              </tr>
                            </thead>
                            <tbody>
                              {stationChargers.map((charger) => (
                                <tr
                                  key={charger.id}
                                  className="border-b border-gray-100 last:border-b-0"
                                >
                                  <td className="px-4 py-2 text-gray-900">
                                    {charger.chargerType || '—'}
                                  </td>
                                  <td className="px-4 py-2 text-gray-900">
                                    {charger.maxRate != null
                                      ? `${Number(charger.maxRate)} kW`
                                      : '—'}
                                  </td>
                                  <td className="px-4 py-2">
                                    {Number(charger.status) === STATION_STATUS_ACTIVE ? (
                                      <span className="text-green-700">Active</span>
                                    ) : (
                                      <span className="text-red-500">Inactive</span>
                                    )}
                                  </td>
                                </tr>
                              ))}
                            </tbody>
                          </table>
                        </div>
                      )
                    })()}
                  </div>
                )}
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  )
}

export default FindStations