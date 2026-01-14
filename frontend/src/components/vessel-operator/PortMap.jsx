import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { CircleMarker, MapContainer, Popup, TileLayer, useMapEvents } from 'react-leaflet'
import 'leaflet/dist/leaflet.css'
import { getApiEndpoint } from '@/config/api'

const DEFAULT_CENTER = [20, 0]
const DEFAULT_ZOOM = 2
const MIN_DISCOVERY_ZOOM = 5

const MapBoundsTracker = ({ onViewportChange }) => {
  const map = useMapEvents({
    moveend: () =>
      onViewportChange({
        bounds: map.getBounds(),
        zoom: map.getZoom()
      }),
    zoomend: () =>
      onViewportChange({
        bounds: map.getBounds(),
        zoom: map.getZoom()
      })
  })

  useEffect(() => {
    onViewportChange({
      bounds: map.getBounds(),
      zoom: map.getZoom()
    })
  }, [map, onViewportChange])

  return null
}

const PortMap = ({
  bookings = [],
  viewMode = 'both',
  onBookingFocus = () => {},
  defaultCenter = DEFAULT_CENTER,
  defaultZoom = DEFAULT_ZOOM
}) => {
  const [nearbyPorts, setNearbyPorts] = useState([])
  const [isLoadingPorts, setIsLoadingPorts] = useState(false)
  const [loadError, setLoadError] = useState(null)
  const [pendingBounds, setPendingBounds] = useState(null)
  const [currentZoom, setCurrentZoom] = useState(defaultZoom)
  const lastBboxRef = useRef(null)

  const bookingPorts = useMemo(() => {
    const grouped = {}

    bookings.forEach((booking) => {
      if (typeof booking.lat !== 'number' || typeof booking.lng !== 'number') {
        return
      }
      const key = booking.stationId || `${booking.lat}-${booking.lng}`
      if (!grouped[key]) {
        grouped[key] = {
          id: key,
          lat: booking.lat,
          lng: booking.lng,
          name: booking.stationName || 'Booking Location',
          country: booking.country || '',
          bookings: []
        }
      }
      grouped[key].bookings.push(booking)
    })

    return Object.values(grouped)
  }, [bookings])

  const bookingPortKeys = useMemo(
    () => new Set(bookingPorts.map((port) => `${port.lat.toFixed(4)}-${port.lng.toFixed(4)}`)),
    [bookingPorts]
  )

  const shouldShowNearbyMarkers = viewMode === 'nearby' && currentZoom >= MIN_DISCOVERY_ZOOM

  const filteredNearbyPorts = useMemo(() => {
    if (!shouldShowNearbyMarkers) return []
    return nearbyPorts.filter((port) => {
      const key = `${port.lat.toFixed(4)}-${port.lng.toFixed(4)}`
      return !bookingPortKeys.has(key)
    })
  }, [nearbyPorts, bookingPortKeys, shouldShowNearbyMarkers])

  const handleViewportChange = useCallback(
    ({ bounds, zoom }) => {
      if (!bounds) return
      setCurrentZoom(zoom)
      const nextBounds = {
        minLat: bounds.getSouth(),
        maxLat: bounds.getNorth(),
        minLng: bounds.getWest(),
        maxLng: bounds.getEast()
      }
      setPendingBounds(nextBounds)
    },
    []
  )

  const fetchPorts = useCallback(async (bounds) => {
    if (!bounds) return
    const bboxString = `${bounds.minLng},${bounds.minLat},${bounds.maxLng},${bounds.maxLat}`
    if (bboxString === lastBboxRef.current) {
      return
    }

    lastBboxRef.current = bboxString
    setIsLoadingPorts(true)
    setLoadError(null)
    try {
      const response = await fetch(
        getApiEndpoint(`/api/ports?bbox=${encodeURIComponent(bboxString)}&limit=250`)
      )
      if (!response.ok) {
        throw new Error('Unable to load ports for this area')
      }
      const payload = await response.json()
      setNearbyPorts(payload?.ports || [])
    } catch (error) {
      setLoadError(error.message || 'Unable to load ports')
    } finally {
      setIsLoadingPorts(false)
    }
  }, [])

  useEffect(() => {
    if (!pendingBounds) return
    const timeout = setTimeout(() => {
      fetchPorts(pendingBounds)
    }, 350)
    return () => clearTimeout(timeout)
  }, [pendingBounds, fetchPorts])

  const handleMarkerClick = useCallback(
    (port) => {
      if (port.bookings?.length) {
        onBookingFocus(port.bookings[0].id)
      }
    },
    [onBookingFocus]
  )

  const mapKey = `${defaultCenter[0]}-${defaultCenter[1]}-${defaultZoom}`
  const shouldShowZoomHint =
    viewMode === 'nearby' &&
    currentZoom < MIN_DISCOVERY_ZOOM &&
    !isLoadingPorts &&
    !loadError

  return (
    <div className="relative h-[420px] w-full overflow-hidden rounded-md border bg-muted/20">
      <MapContainer
        key={mapKey}
        center={defaultCenter}
        zoom={defaultZoom}
        scrollWheelZoom
        className="h-full w-full"
        minZoom={2}
        worldCopyJump
      >
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />
        <MapBoundsTracker onViewportChange={handleViewportChange} />

        {viewMode === 'bookings' &&
          bookingPorts.map((port) => (
            <CircleMarker
              key={`booking-${port.id}`}
              center={[port.lat, port.lng]}
              radius={10}
              pathOptions={{
                color: '#0f172a',
                weight: 2,
                fillColor: '#0ea5e9',
                fillOpacity: 0.9
              }}
              eventHandlers={{
                click: () => handleMarkerClick(port)
              }}
            >
              <Popup>
                <div className="space-y-2">
                  <div>
                    <p className="font-semibold">{port.name}</p>
                    {port.country && (
                      <p className="text-sm text-muted-foreground">{port.country}</p>
                    )}
                  </div>
                  <div className="space-y-1">
                    {port.bookings.map((booking) => (
                      <button
                        key={booking.id}
                        type="button"
                        className="w-full rounded-md border px-2 py-1 text-left text-sm hover:bg-muted"
                        onClick={() => onBookingFocus(booking.id)}
                      >
                        <p className="font-medium">{booking.stationName}</p>
                        <p className="text-xs text-muted-foreground">
                          {booking.formattedDate} • {booking.formattedTime}
                        </p>
                      </button>
                    ))}
                  </div>
                </div>
              </Popup>
            </CircleMarker>
          ))}

        {shouldShowNearbyMarkers &&
          filteredNearbyPorts.map((port) => (
            <CircleMarker
              key={`nearby-${port.id}`}
              center={[port.lat, port.lng]}
              radius={6}
              pathOptions={{
                color: '#475569',
                weight: 1,
                fillColor: '#94a3b8',
                fillOpacity: 0.7
              }}
            >
              <Popup>
                <div>
                  <p className="font-medium">{port.name}</p>
                  {port.country && <p className="text-xs text-muted-foreground">{port.country}</p>}
                </div>
              </Popup>
            </CircleMarker>
          ))}
      </MapContainer>

      {isLoadingPorts && (
        <div className="pointer-events-none absolute inset-0 flex items-center justify-center bg-background/40 text-sm text-muted-foreground">
          Loading ports…
        </div>
      )}
      {shouldShowZoomHint && (
        <div className="absolute bottom-3 left-3 rounded bg-slate-900/80 px-3 py-1 text-xs text-white shadow">
          Zoom in to see nearby ports.
        </div>
      )}
      {loadError && (
        <div className="absolute bottom-3 left-3 rounded bg-red-50 px-3 py-1 text-xs font-medium text-red-600 shadow">
          {loadError}
        </div>
      )}
    </div>
  )
}

export default PortMap
