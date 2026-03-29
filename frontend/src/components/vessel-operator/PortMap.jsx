import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { CircleMarker, MapContainer, Marker, Popup, TileLayer, useMap, useMapEvents } from 'react-leaflet'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'
import { getApiEndpoint } from '@/config/api'

const DEFAULT_CENTER = [20, 0]
const DEFAULT_ZOOM = 2
const MIN_DISCOVERY_ZOOM = 5

const createWaypointIcon = ({ isFocused, bookingCount }) => {
  const fillColor = isFocused ? '#f59e0b' : '#10b981'
  const markerLabel = Number.isFinite(bookingCount) ? bookingCount : ''

  return L.divIcon({
    className: 'custom-marker',
    html: `
      <div style="
        background-color: ${fillColor};
        width: 40px;
        height: 40px;
        border-radius: 50% 50% 50% 0;
        transform: rotate(-45deg);
        border: 2px solid white;
        box-shadow: 0 2px 8px rgba(0,0,0,0.3);
        display: flex;
        align-items: center;
        justify-content: center;
      ">
        <span style="
          transform: rotate(45deg);
          color: white;
          font-weight: bold;
          font-size: 14px;
        ">${markerLabel}</span>
      </div>
    `,
    iconSize: [40, 40],
    iconAnchor: [20, 40],
    popupAnchor: [0, -40]
  })
}

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

const FocusedBookingPopupController = ({
  bookingPorts,
  focusedBookingId,
  markerRefs,
  programmaticPopupPortRef,
  focusZoom
}) => {
  const map = useMap()

  useEffect(() => {
    if (!focusedBookingId) {
      return
    }

    const focusedPort = bookingPorts.find((port) =>
      port.bookings.some((booking) => booking.id === focusedBookingId)
    )
    if (!focusedPort) {
      return
    }

    let marker = markerRefs.current[focusedPort.id]
    if (!marker) {
      const retryId = setTimeout(() => {
        marker = markerRefs.current[focusedPort.id]
        if (!marker) {
          return
        }

        programmaticPopupPortRef.current = focusedPort.id
        const targetZoom = Math.max(map.getZoom(), focusZoom)
        const openPopup = () => {
          marker.openPopup()
        }

        map.once('moveend', openPopup)
        map.flyTo([focusedPort.lat, focusedPort.lng], targetZoom, {
          animate: true,
          duration: 0.5
        })

        setTimeout(openPopup, 700)
      }, 120)

      return () => clearTimeout(retryId)
    }

    programmaticPopupPortRef.current = focusedPort.id
    const targetZoom = Math.max(map.getZoom(), focusZoom)
    const openPopup = () => {
      marker.openPopup()
    }

    map.once('moveend', openPopup)
    map.flyTo([focusedPort.lat, focusedPort.lng], targetZoom, {
      animate: true,
      duration: 0.5
    })

    // Fallback for cases where moveend does not fire as expected.
    const timeoutId = setTimeout(openPopup, 700)
    return () => {
      map.off('moveend', openPopup)
      clearTimeout(timeoutId)
    }
  }, [bookingPorts, focusedBookingId, map, markerRefs, programmaticPopupPortRef, focusZoom])

  return null
}

/**
 * Single child component for MapContainer so the context provider
 * receives exactly one child (avoids "context consumer" / render2 errors
 * with react-leaflet when multiple siblings are passed).
 */
const MapLayers = ({
  viewMode,
  bookingPorts,
  shouldShowNearbyMarkers,
  filteredNearbyPorts,
  handleViewportChange,
  onBookingFocus,
  focusedBookingId,
  focusZoom
}) => {
  const markerRefs = useRef({})
  const programmaticPopupPortRef = useRef(null)
  const [manualPopupPortId, setManualPopupPortId] = useState(null)

  return (
    <>
    <TileLayer
      attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
      url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
    />
    <MapBoundsTracker onViewportChange={handleViewportChange} />
    <FocusedBookingPopupController
      bookingPorts={bookingPorts}
      focusedBookingId={focusedBookingId}
      markerRefs={markerRefs}
      programmaticPopupPortRef={programmaticPopupPortRef}
      focusZoom={focusZoom}
    />

    {viewMode === 'bookings' &&
      bookingPorts.map((port) => {
        const focusedBooking = port.bookings.find((booking) => booking.id === focusedBookingId) || null
        const isManualPopupForPort = manualPopupPortId === port.id
        const shouldShowBookingList = isManualPopupForPort || !focusedBooking

        return (
          <Marker
            key={`booking-${port.id}`}
            position={[port.lat, port.lng]}
            ref={(node) => {
              if (node) {
                markerRefs.current[port.id] = node
              } else {
                delete markerRefs.current[port.id]
              }
            }}
            icon={createWaypointIcon({
              isFocused: Boolean(focusedBooking),
              bookingCount: port.bookings.length
            })}
            eventHandlers={{
              popupopen: () => {
                if (programmaticPopupPortRef.current === port.id) {
                  programmaticPopupPortRef.current = null
                  setManualPopupPortId(null)
                  return
                }

                setManualPopupPortId(port.id)
              },
              popupclose: () => {
                setManualPopupPortId((current) => (current === port.id ? null : current))
              }
            }}
          >
            <Popup closeOnClick={false} autoClose={false}>
              <div className="space-y-3 min-w-[220px]">
                <div>
                  <p className="font-semibold">{port.name}</p>
                  {port.country && (
                    <p className="text-sm text-muted-foreground">{port.country}</p>
                  )}
                </div>
                {focusedBooking && !shouldShowBookingList && (
                  <div className="rounded-md border bg-slate-50 p-2 text-xs space-y-1">
                    <p className="font-semibold text-slate-800">Selected Booking</p>
                    <p className="text-slate-700">{focusedBooking.formattedDate} • {focusedBooking.formattedTime}</p>
                    <p className="text-slate-700">Status: {focusedBooking.status}</p>
                    <p className="text-slate-700">Vessel: {focusedBooking.vessel}</p>
                    <p className="text-slate-700">Type: {focusedBooking.chargerType}</p>
                  </div>
                )}
                {shouldShowBookingList && (
                  <div className="space-y-1">
                    {port.bookings.map((booking) => (
                      <button
                        key={booking.id}
                        type="button"
                        className={`w-full rounded-md border px-2 py-1 text-left text-sm transition-colors ${
                          focusedBookingId === booking.id ? 'bg-muted border-slate-400' : 'hover:bg-muted'
                        }`}
                        onClick={() => {
                          setManualPopupPortId(null)
                          onBookingFocus(booking.id)
                        }}
                      >
                        <p className="font-medium">{booking.stationName}</p>
                        <p className="text-xs text-muted-foreground">
                          {booking.formattedDate} • {booking.formattedTime}
                        </p>
                      </button>
                    ))}
                  </div>
                )}
              </div>
            </Popup>
          </Marker>
        )
      })}

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
              {port.country && (
                <p className="text-xs text-muted-foreground">{port.country}</p>
              )}
            </div>
          </Popup>
        </CircleMarker>
      ))}
    </>
  )
}

const PortMap = ({
  bookings = [],
  viewMode = 'both',
  onBookingFocus = () => {},
  focusedBookingId = null,
  focusZoom = 11,
  defaultCenter = DEFAULT_CENTER,
  defaultZoom = DEFAULT_ZOOM
}) => {
  const [mounted, setMounted] = useState(false)
  const [nearbyPorts, setNearbyPorts] = useState([])
  const [isLoadingPorts, setIsLoadingPorts] = useState(false)
  const [loadError, setLoadError] = useState(null)
  const [pendingBounds, setPendingBounds] = useState(null)
  const [currentZoom, setCurrentZoom] = useState(defaultZoom)
  const lastBboxRef = useRef(null)

  useEffect(() => {
    setMounted(true)
  }, [])

  useEffect(() => {
    setCurrentZoom(defaultZoom)
  }, [defaultZoom])

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

  const visibleBookingPorts = useMemo(() => {
    if (!focusedBookingId) {
      return bookingPorts
    }
    return bookingPorts.filter((port) =>
      port.bookings.some((booking) => booking.id === focusedBookingId)
    )
  }, [bookingPorts, focusedBookingId])

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

  const mapKey = `${defaultCenter[0]}-${defaultCenter[1]}-${defaultZoom}`
  const shouldShowZoomHint =
    viewMode === 'nearby' &&
    currentZoom < MIN_DISCOVERY_ZOOM &&
    !isLoadingPorts &&
    !loadError

  if (!mounted) {
    return (
      <div className="relative h-[420px] w-full overflow-hidden rounded-md border bg-muted/20 flex items-center justify-center text-muted-foreground text-sm">
        Loading map…
      </div>
    )
  }

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
        <MapLayers
          viewMode={viewMode}
          bookingPorts={visibleBookingPorts}
          shouldShowNearbyMarkers={shouldShowNearbyMarkers}
          filteredNearbyPorts={filteredNearbyPorts}
          handleViewportChange={handleViewportChange}
          onBookingFocus={onBookingFocus}
          focusedBookingId={focusedBookingId}
          focusZoom={focusZoom}
        />
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
