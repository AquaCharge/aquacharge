import { useEffect, useState } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Separator } from '@/components/ui/separator'
import { Skeleton } from '@/components/ui/skeleton'
import { Ship } from 'lucide-react'

export default function Vessels() {
  const [vessels, setVessels] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    fetch('/api/vessels')
      .then(response => {
        if (!response.ok) {
          throw new Error('Failed to fetch vessels')
        }
        return response.json()
      })
      .then(setVessels)
      .catch(setError)
      .finally(() => setLoading(false))
  }, [])

  return (
    <div className="flex-1 space-y-4 p-8 pt-6">
      <div className="flex items-center justify-between space-y-2">
        <h2 className="text-3xl font-bold tracking-tight">My Vessels</h2>
        <div className="flex items-center space-x-2">
          <Ship className="h-6 w-6 text-blue-600" />
        </div>
      </div>
      <Separator />
      
      <div className="space-y-4">
        {/* Overview Card */}
        <Card>
          <CardHeader>
            <CardTitle>Fleet Overview</CardTitle>
            <CardDescription>
              {loading ? 'Loading vessels...' : `You have ${vessels.length} vessels registered`}
            </CardDescription>
          </CardHeader>
          <CardContent>
            {loading ? (
              <Skeleton className="h-6 w-32" />
            ) : error ? (
              <Badge variant="destructive">Error loading vessels</Badge>
            ) : (
              <Badge variant="default">{vessels.length} Active Vessels</Badge>
            )}
          </CardContent>
        </Card>

        {/* Vessels Grid */}
        {loading ? (
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
            {[1, 2, 3].map((i) => (
              <Card key={i}>
                <CardHeader className="space-y-2">
                  <Skeleton className="h-4 w-3/4" />
                  <Skeleton className="h-3 w-1/2" />
                </CardHeader>
                <CardContent>
                  <Skeleton className="h-8 w-full" />
                </CardContent>
              </Card>
            ))}
          </div>
        ) : error ? (
          <Card className="border-red-200 bg-red-50">
            <CardContent className="pt-6">
              <p className="text-red-700">Failed to load vessels: {error.message}</p>
            </CardContent>
          </Card>
        ) : vessels.length > 0 ? (
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
            {vessels.map((vessel) => (
              <Card key={vessel.id} className="hover:shadow-md transition-shadow">
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <Ship className="h-5 w-5 text-blue-600" />
                    {vessel.name}
                  </CardTitle>
                  <CardDescription>Vessel ID: {vessel.id}</CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="space-y-2">
                    <div className="flex justify-between items-center">
                      <span className="text-sm font-medium">Battery Capacity</span>
                      <Badge variant="outline">
                        {vessel.capacity} {vessel.units}
                      </Badge>
                    </div>
                    <div className="flex justify-between items-center">
                      <span className="text-sm font-medium">Status</span>
                      <Badge variant="default">Active</Badge>
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        ) : (
          <Card>
            <CardContent className="pt-6">
              <div className="text-center space-y-2">
                <Ship className="h-12 w-12 text-gray-400 mx-auto" />
                <p className="text-gray-500">No vessels registered yet</p>
                <p className="text-sm text-gray-400">Add your first vessel to get started</p>
              </div>
            </CardContent>
          </Card>
        )}
      </div>
    </div>
  )
}