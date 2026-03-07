import { useEffect, useState } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Skeleton } from '@/components/ui/skeleton'
import { Ship } from 'lucide-react'
import PageTitle from '@/components/shared/PageTitle'
import { VesselCardGrid } from '@/components/vessel-operator/VesselCardGrid'
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
      <PageTitle
        title="My Vessels"
        subtitle="Manage your vessels and their charging needs"
      />
      
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
          <VesselCardGrid vessels={vessels} />
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