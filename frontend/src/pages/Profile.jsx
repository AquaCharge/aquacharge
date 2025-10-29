import { useState, useEffect } from 'react'
import { useAuth } from '@/contexts/AuthContext'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Separator } from '@/components/ui/separator'
import { Badge } from '@/components/ui/badge'
import { User, Mail, Shield, Ship, Zap, Calendar, Save, Edit2, X, Check } from 'lucide-react'

export default function Profile() {
  const { user } = useAuth()
  const [isEditing, setIsEditing] = useState(false)
  const [formData, setFormData] = useState({
    displayName: '',
    email: '',
    phone: '',
    organization: ''
  })

  // Update formData when user data changes
  useEffect(() => {
    if (user) {
      setFormData({
        displayName: user.displayName || '',
        email: user.email || '',
        phone: user.phone || '',
        organization: user.organization || ''
      })
    }
  }, [user])

  const handleInputChange = (field, value) => {
    setFormData(prev => ({
      ...prev,
      [field]: value
    }))
  }

  const handleSave = () => {
    // TODO: Implement save functionality with API call
    console.log('Saving profile data:', formData)
    setIsEditing(false)
    // In a real app, you'd make an API call here to update the user
  }

  const handleCancel = () => {
    setFormData({
      displayName: user?.displayName || '',
      email: user?.email || '',
      phone: user?.phone || '',
      organization: user?.organization || ''
    })
    setIsEditing(false)
  }

  return (
    <div className="container mx-auto py-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">Profile</h1>
          <p className="text-muted-foreground">Manage your account settings and preferences</p>
        </div>
      </div>

      <div className="grid gap-6 md:grid-cols-3">
        {/* Profile Overview */}
        <Card className="md:col-span-1">
          <CardHeader className="text-center">
            <div className="w-20 h-20 mx-auto bg-blue-500 rounded-full flex items-center justify-center text-white text-2xl font-bold">
              {user?.displayName?.charAt(0)?.toUpperCase() || 'U'}
            </div>
            <CardTitle className="mt-4">{user?.displayName || 'User'}</CardTitle>
            <CardDescription>{user?.email}</CardDescription>
          </CardHeader>
        </Card>

        {/* Profile Details */}
        <Card className="md:col-span-2">
          <CardHeader>
            <CardTitle>
                <div className="flex items-center justify-between">
                    Account Information
                    {!isEditing && (
                    <Edit2 
                        className="w-5 h-5 text-black cursor-pointer hover:text-gray-600 transition-colors" 
                        onClick={() => setIsEditing(true)}
                    />
                    )}
                    {isEditing && (
                    <div className="flex justify-end space-x-2">
                        <Check className="w-5 h-5 text-green-500 cursor-pointer hover:text-green-600 transition-colors" 
                        onClick={handleSave}>
                        </Check>
                        <X className="w-5 h-5 text-red-500 cursor-pointer hover:text-red-600 transition-colors" 
                        variant="outline" onClick={handleCancel}>
                        </X>
                        
                    </div>
                    )}
                </div>
            </CardTitle>
            <CardDescription>
              {isEditing ? 'Update your account details below' : 'Your current account information'}
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid gap-4 md:grid-cols-2">
              <div className="space-y-2">
                <Label htmlFor="displayName">Display Name</Label>
                {isEditing ? (
                  <Input
                    id="displayName"
                    value={formData.displayName}
                    onChange={(e) => handleInputChange('displayName', e.target.value)}
                    placeholder="Enter your display name"
                  />
                ) : (
                  <div className="px-3 py-2 bg-gray-50 rounded-md text-sm">
                    {user?.displayName || 'Not set'}
                  </div>
                )}
              </div>

              <div className="space-y-2">
                <Label htmlFor="email">Email Address</Label>
                {isEditing ? (
                  <Input
                    id="email"
                    type="email"
                    value={formData.email}
                    onChange={(e) => handleInputChange('email', e.target.value)}
                    placeholder="Enter your email"
                  />
                ) : (
                  <div className="px-3 py-2 bg-gray-50 rounded-md text-sm">
                    {user?.email || 'Not set'}
                  </div>
                )}
              </div>
            </div>

            
          </CardContent>
        </Card>
      </div>

      {/* Additional Settings */}
      <Card>
        <CardHeader>
          <CardTitle>Account Settings</CardTitle>
          <CardDescription>Manage your account preferences and security</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex items-center justify-between py-3 border-b">
            <div>
              <h4 className="font-medium">Change Password</h4>
              <p className="text-sm text-muted-foreground">Update your account password</p>
            </div>
            <Button variant="outline" size="sm">
              Change Password
            </Button>
          </div>
          <div className="flex items-center justify-between py-3">
            <div>
              <h4 className="font-medium">Delete Account</h4>
              <p className="text-sm text-muted-foreground">Permanently delete your account and all data</p>
            </div>
            <Button variant="destructive disabled" size="sm">
              Delete Account
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}