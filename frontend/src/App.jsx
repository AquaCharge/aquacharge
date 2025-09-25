import { useEffect, useState } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Separator } from '@/components/ui/separator'
import { Skeleton } from '@/components/ui/skeleton'

export default function App() {
  const [health, setHealth] = useState(null)
  const [sites, setSites] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    Promise.all([
      fetch('/api/health').then(r => r.json()).then(setHealth),
      fetch('/api/sites').then(r => r.json()).then(setSites)
    ])
    .catch(console.error)
    .finally(() => setLoading(false))
  }, [])

  return (
    <div className="min-h-screen bg-gray-50 p-6">
      <div className="max-w-4xl mx-auto space-y-6">
        {/* Header */}
        <div className="text-center space-y-2">
          <h1 className="text-4xl font-bold text-gray-900">AquaCharge</h1>
          <p className="text-lg text-gray-600">Minimal Starter Dashboard</p>
        </div>

        <Separator />

        {/* Health Status Card */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              Backend Health Status
            </CardTitle>
            <CardDescription>
              Current status of the backend API
            </CardDescription>
          </CardHeader>
          <CardContent>
            {loading ? (
              <Skeleton className="h-6 w-24" />
            ) : (
              <Badge variant={health?.status === 'ok' ? 'default' : 'destructive'}>
                {health ? health.status : 'error'}
              </Badge>
            )}
          </CardContent>
        </Card>

        {/* Sites Card */}
        <Card>
          <CardHeader>
            <CardTitle>Charging Sites</CardTitle>
            <CardDescription>
              {loading ? 'Loading sites...' : `${sites.length} sites available`}
            </CardDescription>
          </CardHeader>
          <CardContent>
            {loading ? (
              <div className="space-y-2">
                <Skeleton className="h-4 w-full" />
                <Skeleton className="h-4 w-3/4" />
                <Skeleton className="h-4 w-1/2" />
              </div>
            ) : sites.length > 0 ? (
              <div className="space-y-3">
                {sites.map(site => (
                  <div key={site.id} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                    <div>
                      <h3 className="font-semibold text-gray-900">{site.name}</h3>
                      <p className="text-sm text-gray-600">{site.city}</p>
                    </div>
                    <Badge variant="outline">Active</Badge>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-gray-500">No sites found</p>
            )}
          </CardContent>
        </Card>

        {/* Footer */}
        <Card className="bg-blue-50 border-blue-200">
          <CardContent className="pt-6">
            <p className="text-sm text-blue-700">
              💡 <strong>Development Tip:</strong> Edit{' '}
              <code className="bg-blue-100 px-1 rounded">frontend/src/App.jsx</code> and{' '}
              <code className="bg-blue-100 px-1 rounded">backend/app.py</code> to continue building.
            </p>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}