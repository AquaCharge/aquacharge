import { useEffect, useMemo, useState } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import { Badge } from '@/components/ui/badge'
import { CalendarPlus, RefreshCw, AlertCircle } from 'lucide-react'
import { useAuth } from '@/contexts/AuthContext'
import { getApiEndpoint } from '@/config/api'

const INITIAL_FORM = {
  stationId: '',
  pricePerKwh: '',
  targetEnergyKwh: '',
  maxParticipants: '',
  startTime: '',
  endTime: '',
  details: '{}',
}

const toIsoString = (value) => {
  if (!value) return ''
  return new Date(value).toISOString()
}

const normalizeStatus = (status) => {
  if (!status) return 'Unknown'
  return String(status)
}

const statusBadgeClass = (status) => {
  const normalized = String(status || '').toLowerCase()
  if (normalized === 'created') return 'bg-blue-100 text-blue-800'
  if (normalized === 'active') return 'bg-emerald-100 text-emerald-800'
  if (normalized === 'completed') return 'bg-slate-100 text-slate-800'
  if (normalized === 'cancelled') return 'bg-rose-100 text-rose-800'
  return 'bg-gray-100 text-gray-800'
}

const isActiveEvent = (status) => String(status || '').toLowerCase() === 'active'

const DREventsManagement = () => {
  const { user } = useAuth()
  const [events, setEvents] = useState([])
  const [stations, setStations] = useState([])
  const [isLoading, setIsLoading] = useState(false)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [error, setError] = useState('')
  const [successMessage, setSuccessMessage] = useState('')
  const [formData, setFormData] = useState(INITIAL_FORM)

  const authToken = localStorage.getItem('auth-token')
  const canViewDREvents = user?.type_name === 'POWER_OPERATOR'

  const stationLookup = useMemo(() => {
    return stations.reduce((accumulator, station) => {
      accumulator[station.id] = station.displayName || station.id
      return accumulator
    }, {})
  }, [stations])

  const activeEvents = useMemo(() => {
    return [...events]
      .filter((drEvent) => isActiveEvent(drEvent.status))
      .sort((left, right) => {
        const leftTime = new Date(left.startTime || 0).getTime()
        const rightTime = new Date(right.startTime || 0).getTime()
        return rightTime - leftTime
      })
  }, [events])

  const loadStations = async () => {
    const response = await fetch(getApiEndpoint('/api/stations'))
    if (!response.ok) {
      throw new Error('Failed to load stations')
    }
    const payload = await response.json()
    setStations(Array.isArray(payload) ? payload : [])
  }

  const loadEvents = async () => {
    if (!authToken) {
      setError('Missing authentication token.')
      return
    }

    setIsLoading(true)
    setError('')
    try {
      const response = await fetch(getApiEndpoint('/api/drevents'), {
        headers: {
          Authorization: `Bearer ${authToken}`,
        },
      })

      if (!response.ok) {
        const responsePayload = await response.json().catch(() => ({}))
        throw new Error(
          responsePayload.details || responsePayload.error || 'Failed to load DR events'
        )
      }

      const payload = await response.json()
      setEvents(Array.isArray(payload) ? payload : [])
    } catch (loadError) {
      setError(loadError.message || 'Unable to load DR events.')
    } finally {
      setIsLoading(false)
    }
  }

  useEffect(() => {
    if (!canViewDREvents) {
      return
    }

    const fetchData = async () => {
      try {
        await Promise.all([loadStations(), loadEvents()])
      } catch (loadError) {
        setError(loadError.message || 'Failed to load DR event data.')
      }
    }

    fetchData()
  }, [canViewDREvents, user])

  const handleFieldChange = (field, value) => {
    setFormData((previous) => ({ ...previous, [field]: value }))
  }

  const handleSubmit = async (event) => {
    event.preventDefault()
    setError('')
    setSuccessMessage('')

    if (!authToken) {
      setError('Missing authentication token.')
      return
    }

    let parsedDetails = {}
    try {
      parsedDetails = formData.details ? JSON.parse(formData.details) : {}
    } catch {
      setError('Details must be valid JSON.')
      return
    }

    const payload = {
      stationId: formData.stationId,
      pricePerKwh: Number(formData.pricePerKwh),
      targetEnergyKwh: Number(formData.targetEnergyKwh),
      maxParticipants: Number(formData.maxParticipants),
      startTime: toIsoString(formData.startTime),
      endTime: toIsoString(formData.endTime),
      details: parsedDetails,
    }

    setIsSubmitting(true)
    try {
      const response = await fetch(getApiEndpoint('/api/drevents'), {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${authToken}`,
        },
        body: JSON.stringify(payload),
      })

      if (!response.ok) {
        const responsePayload = await response.json().catch(() => ({}))
        throw new Error(responsePayload.error || 'Failed to create DR event')
      }

      setFormData(INITIAL_FORM)
      setSuccessMessage('DR event created successfully.')
      await loadEvents()
    } catch (submitError) {
      setError(submitError.message || 'Failed to create DR event.')
    } finally {
      setIsSubmitting(false)
    }
  }

  if (!canViewDREvents) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-center">
          <AlertCircle className="h-12 w-12 text-red-500 mx-auto mb-4" />
          <h3 className="text-lg font-semibold text-gray-900 mb-2">Access Denied</h3>
          <p className="text-gray-600">Only power operator accounts can access DR events.</p>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">DR Event Creation</h1>
          <p className="text-gray-600 mt-2">Create demand-response events for vessel dispatch</p>
        </div>
        <Button type="button" variant="outline" onClick={loadEvents} disabled={isLoading}>
          <RefreshCw className="h-4 w-4 mr-2" />
          Refresh
        </Button>
      </div>

      {error && (
        <div className="rounded-md border border-red-200 bg-red-50 p-3 text-sm text-red-700">{error}</div>
      )}
      {successMessage && (
        <div className="rounded-md border border-green-200 bg-green-50 p-3 text-sm text-green-700">
          {successMessage}
        </div>
      )}

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <CalendarPlus className="h-5 w-5" />
            Create DR Event
          </CardTitle>
          <CardDescription>Fields match the DREvent object model and backend API contract.</CardDescription>
        </CardHeader>
        <CardContent>
          <form className="grid grid-cols-1 md:grid-cols-2 gap-4" onSubmit={handleSubmit}>
            <div className="space-y-2">
              <Label htmlFor="stationId">Station</Label>
              <select
                id="stationId"
                className="w-full h-9 rounded-md border border-input bg-background px-3 py-1 text-sm"
                value={formData.stationId}
                onChange={(event) => handleFieldChange('stationId', event.target.value)}
                required
              >
                <option value="">Select station</option>
                {stations.map((station) => (
                  <option key={station.id} value={station.id}>
                    {station.displayName || station.id}
                  </option>
                ))}
              </select>
            </div>

            <div className="space-y-2">
              <Label htmlFor="maxParticipants">Max Participants</Label>
              <Input
                id="maxParticipants"
                type="number"
                min="1"
                step="1"
                value={formData.maxParticipants}
                onChange={(event) => handleFieldChange('maxParticipants', event.target.value)}
                required
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="pricePerKwh">Price per kWh</Label>
              <Input
                id="pricePerKwh"
                type="number"
                min="0"
                step="0.01"
                value={formData.pricePerKwh}
                onChange={(event) => handleFieldChange('pricePerKwh', event.target.value)}
                required
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="targetEnergyKwh">Target Energy (kWh)</Label>
              <Input
                id="targetEnergyKwh"
                type="number"
                min="0"
                step="0.1"
                value={formData.targetEnergyKwh}
                onChange={(event) => handleFieldChange('targetEnergyKwh', event.target.value)}
                required
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="startTime">Start Time</Label>
              <Input
                id="startTime"
                type="datetime-local"
                value={formData.startTime}
                onChange={(event) => handleFieldChange('startTime', event.target.value)}
                required
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="endTime">End Time</Label>
              <Input
                id="endTime"
                type="datetime-local"
                value={formData.endTime}
                onChange={(event) => handleFieldChange('endTime', event.target.value)}
                required
              />
            </div>

            <div className="space-y-2 md:col-span-2">
              <Label htmlFor="details">Details (JSON)</Label>
              <Textarea
                id="details"
                value={formData.details}
                onChange={(event) => handleFieldChange('details', event.target.value)}
                rows={4}
              />
            </div>

            <div className="md:col-span-2">
              <Button type="submit" disabled={isSubmitting}>
                {isSubmitting ? 'Creating...' : 'Create DR Event'}
              </Button>
            </div>
          </form>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Existing DR Events</CardTitle>
          <CardDescription>
            Showing all active demand-response events from the DR events table.
          </CardDescription>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <p className="text-sm text-gray-500">Loading DR events...</p>
          ) : activeEvents.length === 0 ? (
            <p className="text-sm text-gray-500">No active DR events found.</p>
          ) : (
            <div className="space-y-3">
              {activeEvents.map((drEvent) => (
                <div key={drEvent.id} className="rounded-md border p-3">
                  <div className="flex items-center justify-between gap-4">
                    <p className="text-sm font-medium text-gray-900">{drEvent.id}</p>
                    <Badge className={statusBadgeClass(drEvent.status)}>
                      {normalizeStatus(drEvent.status)}
                    </Badge>
                  </div>
                  <p className="text-sm text-gray-600 mt-1">
                    Station: {stationLookup[drEvent.stationId] || drEvent.stationId}
                  </p>
                  <p className="text-sm text-gray-600">
                    {Number(drEvent.targetEnergyKwh)} kWh @ ${Number(drEvent.pricePerKwh)}/kWh
                  </p>
                  <p className="text-xs text-gray-500 mt-1">
                    {new Date(drEvent.startTime).toLocaleString()} - {new Date(drEvent.endTime).toLocaleString()}
                  </p>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}

export default DREventsManagement
