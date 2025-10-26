import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'

const ManageChargers = () => {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-gray-900">Manage Chargers</h1>
        <p className="text-gray-600 mt-2">Monitor and control individual charging units</p>
      </div>
      
      <Card>
        <CardHeader>
          <CardTitle>Charger Management</CardTitle>
          <CardDescription>This page will contain charger management functionality</CardDescription>
        </CardHeader>
        <CardContent>
          <p className="text-gray-600">Charger management features will be implemented here.</p>
        </CardContent>
      </Card>
    </div>
  )
}

export default ManageChargers