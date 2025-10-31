import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Calendar, Clock, MapPin, Zap } from 'lucide-react'

const MyBookings = () => {
  // Mock booking data
  const bookings = [
    {
      id: 1,
      stationName: "Marina Bay Station",
      date: "2025-10-27",
      time: "14:00 - 16:00",
      status: "confirmed",
      vessel: "Sea Breeze",
      chargerType: "Level 2 - 240V",
      location: "Marina Bay, CA"
    },
    {
      id: 2,
      stationName: "Harbor Point Station",
      date: "2025-10-28",
      time: "10:00 - 12:00",
      status: "confirmed",
      vessel: "Ocean Explorer",
      chargerType: "DC Fast Charge",
      location: "Harbor Point, CA"
    },
    {
      id: 3,
      stationName: "Sunset Marina",
      date: "2025-10-25",
      time: "16:00 - 18:00",
      status: "completed",
      vessel: "Sea Breeze",
      chargerType: "Level 2 - 240V",
      location: "Sunset Bay, CA"
    },
    {
      id: 4,
      stationName: "North Harbor Station",
      date: "2025-10-30",
      time: "09:00 - 11:00",
      status: "pending",
      vessel: "Wave Runner",
      chargerType: "Level 1 - 120V",
      location: "North Harbor, CA"
    }
  ]

  const getStatusColor = (status) => {
    switch (status) {
      case 'confirmed':
        return 'bg-green-100 text-green-800'
      case 'pending':
        return 'bg-yellow-100 text-yellow-800'
      case 'completed':
        return 'bg-gray-100 text-gray-800'
      default:
        return 'bg-gray-100 text-gray-800'
    }
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-gray-900">My Bookings</h1>
        <p className="text-gray-600 mt-2">Manage your charging station reservations</p>
      </div>

      {/* Booking Statistics */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Upcoming Bookings</CardTitle>
            <Calendar className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">3</div>
            <p className="text-xs text-muted-foreground">Next 7 days</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Sessions</CardTitle>
            <Zap className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">28</div>
            <p className="text-xs text-muted-foreground">This month</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Hours Charged</CardTitle>
            <Clock className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">56h</div>
            <p className="text-xs text-muted-foreground">This month</p>
          </CardContent>
        </Card>
      </div>

      {/* Bookings List */}
      <Card>
        <CardHeader>
          <CardTitle>All Bookings</CardTitle>
          <CardDescription>Your charging station reservations and history</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {bookings.map((booking) => (
              <div key={booking.id} className="border rounded-lg p-4 hover:bg-gray-50 transition-colors">
                <div className="flex items-start justify-between">
                  <div className="space-y-1">
                    <div className="flex items-center space-x-2">
                      <h3 className="font-semibold text-lg">{booking.stationName}</h3>
                      <span className={`px-2 py-1 rounded-full text-xs font-medium ${getStatusColor(booking.status)}`}>
                        {booking.status.charAt(0).toUpperCase() + booking.status.slice(1)}
                      </span>
                    </div>
                    <div className="flex items-center space-x-4 text-sm text-gray-600">
                      <div className="flex items-center space-x-1">
                        <Calendar className="h-4 w-4" />
                        <span>{booking.date}</span>
                      </div>
                      <div className="flex items-center space-x-1">
                        <Clock className="h-4 w-4" />
                        <span>{booking.time}</span>
                      </div>
                      <div className="flex items-center space-x-1">
                        <MapPin className="h-4 w-4" />
                        <span>{booking.location}</span>
                      </div>
                    </div>
                    <div className="flex items-center space-x-4 text-sm">
                      <span className="text-gray-600">Vessel: <span className="font-medium">{booking.vessel}</span></span>
                      <span className="text-gray-600">Type: <span className="font-medium">{booking.chargerType}</span></span>
                    </div>
                  </div>
                  <div className="flex space-x-2">
                    {booking.status === 'confirmed' && (
                      <>
                        <button className="px-3 py-1 text-sm border rounded-md hover:bg-gray-50 transition-colors">
                          Modify
                        </button>
                        <button className="px-3 py-1 text-sm text-red-600 border border-red-200 rounded-md hover:bg-red-50 transition-colors">
                          Cancel
                        </button>
                      </>
                    )}
                    {booking.status === 'pending' && (
                      <button className="px-3 py-1 text-sm text-red-600 border border-red-200 rounded-md hover:bg-red-50 transition-colors">
                        Cancel
                      </button>
                    )}
                    {booking.status === 'completed' && (
                      <button className="px-3 py-1 text-sm border rounded-md hover:bg-gray-50 transition-colors">
                        View Details
                      </button>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  )
}

export default MyBookings