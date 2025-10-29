import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'

const ManageStations = () => {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-gray-900">Manage Stations</h1>
        <p className="text-gray-600 mt-2">Oversee and configure your charging stations</p>
      </div>
      
      <Card>
        <CardHeader>
          <CardTitle>Station Management</CardTitle>
          <CardDescription>This page will contain station management functionality</CardDescription>
        </CardHeader>
        <CardContent>
          <p className="text-gray-600">Station management features will be implemented here.</p>
        </CardContent>
      </Card>
    </div>
  )
}

export default ManageStations