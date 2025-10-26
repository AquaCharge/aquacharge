import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'

const Analytics = () => {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-gray-900">Analytics</h1>
        <p className="text-gray-600 mt-2">Detailed performance metrics and insights</p>
      </div>
      
      <Card>
        <CardHeader>
          <CardTitle>Performance Analytics</CardTitle>
          <CardDescription>This page will contain detailed analytics and reporting</CardDescription>
        </CardHeader>
        <CardContent>
          <p className="text-gray-600">Analytics dashboard will be implemented here.</p>
        </CardContent>
      </Card>
    </div>
  )
}

export default Analytics