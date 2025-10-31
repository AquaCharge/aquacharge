import { useAuth } from '@/contexts/AuthContext'
import { User, Zap } from 'lucide-react'

const UserTypeIndicator = () => {
  const { user } = useAuth()

  if (!user) return null

  const isVesselOperator = user.type_name === 'VESSEL_OPERATOR'
  const isPowerOperator = user.type_name === 'POWER_OPERATOR'

  return (
    <div className="flex items-center space-x-2 px-3 py-1 rounded-full bg-gray-100">
      {isVesselOperator && (
        <>
          <User className="h-4 w-4 text-blue-600" />
          <span className="text-sm font-medium text-blue-800">Vessel Operator</span>
        </>
      )}
      {isPowerOperator && (
        <>
          <Zap className="h-4 w-4 text-green-600" />
          <span className="text-sm font-medium text-green-800">Power Operator</span>
        </>
      )}
    </div>
  )
}

export default UserTypeIndicator