import { useState, useEffect } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import { Badge } from '@/components/ui/badge'
import { Separator } from '@/components/ui/separator'
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog'
import { 
  Calendar, 
  Clock, 
  Zap, 
  DollarSign, 
  Plus, 
  Users, 
  TrendingUp, 
  AlertCircle,
  CheckCircle,
  XCircle,
  Edit2,
  Trash2
} from 'lucide-react'

export default function DemandResponse() {
  const [events, setEvents] = useState([])
  const [isCreateDialogOpen, setIsCreateDialogOpen] = useState(false)
  const [formData, setFormData] = useState({
    title: '',
    notes: '',
    startTime: '',
    endTime: '',
    powerNeeded: '',
    pricePerKwh: '',
    location: '',
    priority: 'medium'
  })

  // Sample data for demonstration
  useEffect(() => {
    const sampleEvents = [
      // Active Events
      {
        id: 'dr-001',
        title: 'Peak Hour Demand Response',
        notes: 'High demand expected during evening peak hours',
        startTime: '2025-11-03T17:00',
        endTime: '2025-11-03T21:00',
        powerNeeded: 500,
        pricePerKwh: 0.25,
        location: 'Harbor District',
        priority: 'high',
        status: 'active',
        participatingVessels: 12,
        committedPower: 320,
        createdAt: '2025-10-29T10:00:00'
      },
      {
        id: 'dr-002',
        title: 'Grid Stabilization Event',
        notes: 'Emergency grid support needed for maintenance work',
        startTime: '2025-10-31T14:00',
        endTime: '2025-10-31T16:00',
        powerNeeded: 200,
        pricePerKwh: 0.30,
        location: 'Marina Bay',
        priority: 'critical',
        status: 'pending',
        participatingVessels: 0,
        committedPower: 0,
        createdAt: '2025-10-29T14:30:00'
      },
      // Past Events
      {
        id: 'dr-003',
        title: 'Scheduled Load Relief',
        notes: 'Planned demand response for equipment upgrade',
        startTime: '2025-10-28T09:00',
        endTime: '2025-10-28T12:00',
        powerNeeded: 150,
        pricePerKwh: 0.20,
        location: 'Port Authority',
        priority: 'medium',
        status: 'completed',
        participatingVessels: 8,
        committedPower: 150,
        createdAt: '2025-10-27T16:45:00'
      },
      {
        id: 'dr-004',
        title: 'Weekend Peak Management',
        notes: 'Saturday evening demand spike management',
        startTime: '2025-10-26T18:00',
        endTime: '2025-10-26T22:00',
        powerNeeded: 300,
        pricePerKwh: 0.22,
        location: 'Harbor District',
        priority: 'high',
        status: 'completed',
        participatingVessels: 15,
        committedPower: 280,
        createdAt: '2025-10-25T14:20:00'
      },
      {
        id: 'dr-005',
        title: 'Emergency Grid Support',
        notes: 'Unplanned outage response',
        startTime: '2025-10-24T13:00',
        endTime: '2025-10-24T15:00',
        powerNeeded: 400,
        pricePerKwh: 0.35,
        location: 'Marina Bay',
        priority: 'critical',
        status: 'completed',
        participatingVessels: 18,
        committedPower: 400,
        createdAt: '2025-10-24T12:45:00'
      },
      {
        id: 'dr-006',
        title: 'Maintenance Window Support',
        notes: 'Planned maintenance coverage',
        startTime: '2025-10-22T10:00',
        endTime: '2025-10-22T14:00',
        powerNeeded: 250,
        pricePerKwh: 0.18,
        location: 'Port Authority',
        priority: 'medium',
        status: 'completed',
        participatingVessels: 10,
        committedPower: 245,
        createdAt: '2025-10-21T11:30:00'
      },
      {
        id: 'dr-007',
        title: 'Morning Rush Coverage',
        notes: 'Early morning demand response',
        startTime: '2025-10-20T07:00',
        endTime: '2025-10-20T09:00',
        powerNeeded: 180,
        pricePerKwh: 0.28,
        location: 'Harbor District',
        priority: 'high',
        status: 'completed',
        participatingVessels: 6,
        committedPower: 120,
        createdAt: '2025-10-19T16:00:00'
      }
    ]
    setEvents(sampleEvents)
  }, [])

  const handleInputChange = (field, value) => {
    setFormData(prev => ({
      ...prev,
      [field]: value
    }))
  }

  const handleCreateEvent = () => {
    const newEvent = {
      id: `dr-${Date.now()}`,
      ...formData,
      powerNeeded: parseFloat(formData.powerNeeded),
      pricePerKwh: parseFloat(formData.pricePerKwh),
      status: 'pending',
      participatingVessels: 0,
      committedPower: 0,
      createdAt: new Date().toISOString()
    }

    setEvents(prev => [newEvent, ...prev])
    setFormData({
      title: '',
      notes: '',
      startTime: '',
      endTime: '',
      powerNeeded: '',
      pricePerKwh: '',
      location: '',
      priority: 'medium'
    })
    setIsCreateDialogOpen(false)
  }

  const formatDateTime = (dateTimeStr) => {
    return new Date(dateTimeStr).toLocaleString('en-US', {
      month: 'short',
      day: 'numeric',
      hour: 'numeric',
      minute: '2-digit'
    })
  }

  const formatDateRange = (startDateTimeStr, endDateTimeStr) => {
    const start = new Date(startDateTimeStr)
    const end = new Date(endDateTimeStr)
    return `
    ${end.toLocaleString('en-US', {
      day: 'numeric',
      month: 'short',
    })} •
    ${start.toLocaleString('en-US', {
      hour: 'numeric',
      minute: '2-digit'
    })} - ${end.toLocaleString('en-US', {
      hour: 'numeric',
      minute: '2-digit',
    })}
    `
  }

  const calculateDuration = (start, end) => {
    const startTime = new Date(start)
    const endTime = new Date(end)
    const diffMs = endTime - startTime
    const diffHours = diffMs / (1000 * 60 * 60)
    return `${diffHours}h`
  }

  // Separate active and past events
  const activeEvents = events.filter(event => event.status === 'active' || event.status === 'pending')
  const pastEvents = events.filter(event => event.status === 'completed' || event.status === 'cancelled')

  // Calculate historical metrics
  const calculateHistoricalMetrics = () => {
    if (pastEvents.length === 0) {
      return {
        totalEvents: 0,
        avgFulfillmentRate: 0,
        totalPowerDelivered: 0,
        avgPricePerKwh: 0,
        mostSuccessfulPriority: 'N/A',
        totalVesselParticipations: 0
      }
    }

    const totalPowerRequested = pastEvents.reduce((sum, event) => sum + event.powerNeeded, 0)
    const totalPowerDelivered = pastEvents.reduce((sum, event) => sum + event.committedPower, 0)
    const avgFulfillmentRate = totalPowerRequested > 0 ? (totalPowerDelivered / totalPowerRequested) * 100 : 0
    const avgPricePerKwh = pastEvents.reduce((sum, event) => sum + event.pricePerKwh, 0) / pastEvents.length
    const totalVesselParticipations = pastEvents.reduce((sum, event) => sum + event.participatingVessels, 0)

    // Calculate most successful priority level
    const priorityStats = pastEvents.reduce((acc, event) => {
      const rate = event.powerNeeded > 0 ? (event.committedPower / event.powerNeeded) * 100 : 0
      if (!acc[event.priority]) {
        acc[event.priority] = { total: 0, count: 0 }
      }
      acc[event.priority].total += rate
      acc[event.priority].count += 1
      return acc
    }, {})

    const mostSuccessfulPriority = Object.entries(priorityStats).reduce((best, [priority, stats]) => {
      const avgRate = stats.total / stats.count
      return avgRate > best.rate ? { priority, rate: avgRate } : best
    }, { priority: 'N/A', rate: 0 }).priority

    return {
      totalEvents: pastEvents.length,
      avgFulfillmentRate: Math.round(avgFulfillmentRate),
      totalPowerDelivered: Math.round(totalPowerDelivered),
      avgPricePerKwh: avgPricePerKwh,
      mostSuccessfulPriority,
      totalVesselParticipations
    }
  }

  const historicalMetrics = calculateHistoricalMetrics()

  return (
    <div className="container mx-auto py-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">Demand Response Events</h1>
          <p className="text-muted-foreground">Create and manage demand response events for vessel operators</p>
        </div>
        
        <Dialog open={isCreateDialogOpen} onOpenChange={setIsCreateDialogOpen}>
          <DialogTrigger asChild>
            <Button>
              <Plus className="w-4 h-4 mr-2" />
              Create Event
            </Button>
          </DialogTrigger>
          <DialogContent className="max-w-2xl">
            <DialogHeader>
              <DialogTitle>Create Demand Response Event</DialogTitle>
              <DialogDescription>
                Set up a new demand response event to request power discharge from vessel operators
              </DialogDescription>
            </DialogHeader>
            
            <div className="grid gap-4 py-4">
              
              
              
              <div className="grid grid-cols-2 gap-4">
                <div className="grid gap-2">
                  <Label htmlFor="startTime">Start Time</Label>
                  <Input
                    id="startTime"
                    type="datetime-local"
                    value={formData.startTime}
                    onChange={(e) => handleInputChange('startTime', e.target.value)}
                  />
                </div>
                <div className="grid gap-2">
                  <Label htmlFor="endTime">End Time</Label>
                  <Input
                    id="endTime"
                    type="datetime-local"
                    value={formData.endTime}
                    onChange={(e) => handleInputChange('endTime', e.target.value)}
                  />
                </div>
              </div>
              
              <div className="grid grid-cols-2 gap-4">
                <div className="grid gap-2">
                  <Label htmlFor="powerNeeded">Power Needed (kWh)</Label>
                  <Input
                    id="powerNeeded"
                    type="number"
                    step="0.1"
                    value={formData.powerNeeded}
                    onChange={(e) => handleInputChange('powerNeeded', e.target.value)}
                    placeholder="500"
                  />
                </div>
                <div className="grid gap-2">
                  <Label htmlFor="pricePerKwh">Price per kWh ($)</Label>
                  <Input
                    id="pricePerKwh"
                    type="number"
                    step="0.01"
                    value={formData.pricePerKwh}
                    onChange={(e) => handleInputChange('pricePerKwh', e.target.value)}
                    placeholder="0.25"
                  />
                </div>
              </div>
              <div className="grid gap-2">
                <Label htmlFor="notes">Notes</Label>
                <Textarea
                  id="notes"
                  value={formData.notes}
                  onChange={(e) => handleInputChange('notes', e.target.value)}
                  placeholder="Add notes about the purpose and context of this demand response event"
                  rows={3}
                />
              
              </div>
            </div>
            
            <div className="flex justify-end space-x-2">
              <Button variant="outline" onClick={() => setIsCreateDialogOpen(false)}>
                Cancel
              </Button>
              <Button onClick={handleCreateEvent}>
                Create Event
              </Button>
            </div>
          </DialogContent>
        </Dialog>
      </div>

        {/* Active Events Section */}
        <div>
          <h1 className="text-2xl font-semibold">Active Events</h1>
        </div>
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {activeEvents.map((event) => (
            <Card key={event.id} className="border-l">
            <CardContent>
                <div className="flex justify-between">
                <div className="space-y-1">
                    <div className="flex justify-between">
                      <h3 className="font-semibold">{formatDateRange(event.startTime, event.endTime)}</h3>
                    </div>
                    <div className="flex items-center space-x-4 text-sm text-muted-foreground">
                  
                    <div className="flex items-center">
                        <Clock className="w-4 h-4 mr-1" />
                        {calculateDuration(event.startTime, event.endTime)}
                    </div>
                    <div className="flex items-center">
                        <Zap className="w-4 h-4 mr-1" />
                        {event.powerNeeded} kWh
                    </div>
                    <div className="flex items-center">
                        <DollarSign className="w-4 h-4 mr-1" />
                        ${event.pricePerKwh}/kWh
                    </div>
                    </div>
                </div>
                
                </div>
                
                <Separator className="my-4" />
                
                <div className="grid grid-cols-1 gap-6 text-sm">
                

                {/* Power Commitment Chart */}
                <div className="space-y-2">
                    <div className="flex items-center justify-between">
                    <div className="font-medium flex items-center">
                        Power Committed
                    </div>
                    <span>{event.committedPower}/{event.powerNeeded} kWh</span>
                    </div>
                    <div className="space-y-1">
                    
                    <div className="w-full bg-gray-200 rounded-full h-2">
                        <div 
                        className={`h-2 rounded-full transition-all duration-300 ${
                            event.powerNeeded > 0 && (event.committedPower / event.powerNeeded) >= 0.9 
                            ? 'bg-green-600' 
                            : event.powerNeeded > 0 && (event.committedPower / event.powerNeeded) >= 0.7 
                            ? 'bg-yellow-500' 
                            : 'bg-red-500'
                        }`}
                        style={{ width: `${Math.min(100, event.powerNeeded > 0 ? (event.committedPower / event.powerNeeded) * 100 : 0)}%` }}
                        ></div>
                    </div>
                    <div className="flex justify-between text-xs text-muted-foreground">
                        <span className={`font-medium ${
                        event.powerNeeded > 0 && (event.committedPower / event.powerNeeded) >= 0.9 
                            ? 'text-green-600' 
                            : event.powerNeeded > 0 && (event.committedPower / event.powerNeeded) >= 0.7 
                            ? 'text-yellow-600' 
                            : 'text-red-600'
                        }`}>
                        {event.powerNeeded > 0 ? Math.round((event.committedPower / event.powerNeeded) * 100) : 0}% fulfilled
                        </span>
                    </div>
                    
                    </div>
                </div>

                {/* Forecast Timeline Chart */}
                <div className="space-y-2">
                    <div className="flex items-center justify-between">
                    <div className="font-medium flex items-center">
                        Forecast Timeline
                    </div>
                  
                    </div>
                    <div className="space-y-1">
                    <div className="flex justify-between text-xs text-muted-foreground">
                        <span>Created → Event Start</span>
                        <span>
                        {(() => {
                            const created = new Date(event.createdAt)
                            const start = new Date(event.startTime)
                            const totalHours = (start - created) / (1000 * 60 * 60)
                            if (totalHours < 24) return `${Math.round(totalHours)}h total`
                            return `${Math.round(totalHours / 24)}d total`
                        })()}
                        </span>
                    </div>
                    <div className="w-full bg-gray-200 rounded-full h-2">
                        <div 
                        className="bg-black h-2 rounded-full transition-all duration-300" 
                        style={{ 
                            width: `${(() => {
                            const now = new Date()
                            const created = new Date(event.createdAt)
                            const start = new Date(event.startTime)
                            if (now >= start) return 100 // Event has started
                            const totalTime = start - created // Total forecast period
                            const elapsed = now - created // Time since creation
                            return Math.min(100, Math.max(0, (elapsed / totalTime) * 100))
                            })()}%` 
                        }}
                        ></div>
                    </div>
                    <div className="flex justify-between text-xs">
                        <span className="text-black font-medium">
                        {(() => {
                            const now = new Date()
                            const created = new Date(event.createdAt)
                            const start = new Date(event.startTime)
                            if (now >= start) return 'Event started'
                            const totalTime = start - created
                            const elapsed = now - created
                            const progress = Math.round((elapsed / totalTime) * 100)
                            return `${progress}% to event start`
                        })()}
                        </span>
                    </div>
                    </div>
                </div>
                </div>

                {/* Quick Stats Row */}
                <div className="mt-4 flex items-center justify-between text-xs text-muted-foreground bg-gray-50 rounded-lg p-3">
                <div className="flex items-center space-x-4">
                    <div className="flex items-center">
                    ${(event.powerNeeded * event.pricePerKwh).toFixed(0)} max payout
                    </div>
                </div>
                <div className="flex items-center space-x-2">
                    <div className={`flex items-center px-2 py-1 rounded-full text-xs font-medium ${
                    event.status === 'active' 
                        ? 'bg-green-100 text-green-800' 
                        : 'bg-yellow-100 text-yellow-800'
                    }`}>
                    <div className={`w-2 h-2 rounded-full mr-1 ${
                        event.status === 'active' ? 'bg-green-600' : 'bg-yellow-600'
                    }`}></div>
                    {event.status === 'active' ? 'Live' : 'Pending'}
                    </div>
                </div>
                </div>
            </CardContent>
            </Card>
        ))}
        
        {activeEvents.length === 0 && (
            <div className="text-center py-8 text-muted-foreground">
            <AlertCircle className="w-12 h-12 mx-auto mb-4 opacity-50" />
            <p>No active demand response events.</p>
            <p className="text-sm">Create your first event to start managing power demand.</p>
            </div>
        )}
        </div>

      {/* Past Events Section */}
        <h1 className="text-2xl font-semibold">Past Events</h1>
          <div className="space-y-4">
            {pastEvents.map((event) => (
              <Card key={event.id} className="border-l-4 border-l-gray-500">
                <CardContent>
                  <div className="flex items-start justify-between">
                    <div className="space-y-1">
                      <div className="flex items-center space-x-2">
                        <h3 className="font-semibold">{formatDateRange(event.startTime, event.endTime)}</h3>
                      </div>
                      <p className="text-sm text-muted-foreground">{event.notes}</p>
                      <div className="flex items-center space-x-4 text-sm text-muted-foreground">
                        <div className="flex items-center">
                          <Clock className="w-4 h-4 mr-1" />
                          {calculateDuration(event.startTime, event.endTime)}
                        </div>
                        <div className="flex items-center">
                          <Zap className="w-4 h-4 mr-1" />
                          {event.powerNeeded} kWh requested
                        </div>
                        <div className="flex items-center">
                          <DollarSign className="w-4 h-4 mr-1" />
                          ${event.pricePerKwh}/kWh
                        </div>
                      </div>
                    </div>
                  </div>
                  
                  <Separator className="my-4" />
                  
                  <div className="grid grid-cols-4 gap-4 text-sm">
                    <div>
                      <div className="font-medium">Participating Vessels</div>
                      <div className="text-muted-foreground">{event.participatingVessels} vessels</div>
                    </div>
                    <div>
                      <div className="font-medium">Power Delivered</div>
                      <div className="text-muted-foreground">{event.committedPower} kWh</div>
                    </div>
                    <div>
                      <div className="font-medium">Fulfillment Rate</div>
                      <div className={`font-semibold ${
                        event.powerNeeded > 0 && (event.committedPower / event.powerNeeded) >= 0.9 
                          ? 'text-green-600' 
                          : event.powerNeeded > 0 && (event.committedPower / event.powerNeeded) >= 0.7 
                          ? 'text-yellow-600' 
                          : 'text-red-600'
                      }`}>
                        {event.powerNeeded > 0 ? Math.round((event.committedPower / event.powerNeeded) * 100) : 0}%
                      </div>
                    </div>
                    <div>
                      <div className="font-medium">Total Payout</div>
                      <div className="text-muted-foreground">
                        ${(event.committedPower * event.pricePerKwh).toFixed(2)}
                      </div>
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))}
            
            {pastEvents.length === 0 && (
              <div className="text-center py-8 text-muted-foreground">
                <AlertCircle className="w-12 h-12 mx-auto mb-4 opacity-50" />
                <p>No past events yet.</p>
                <p className="text-sm">Historical performance metrics will appear here once events are completed.</p>
              </div>
            )}
          </div>
    </div>
  )
}