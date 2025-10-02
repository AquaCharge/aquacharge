import MapView from '../components/partials/MapView';

export default function Stations() {
  return (
    <div className="p-6">
      <h1 className="text-3xl font-bold mb-4">Stations</h1>
      <MapView />
      <p className="text-gray-600">Manage your charging bookings and view available stations</p>
    </div>
  )
}