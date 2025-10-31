# AquaCharge Route-Based Architecture Implementation

## Overview
This document outlines the route-based architecture implementation for AquaCharge, providing separate application views for different user types while maximizing code reuse.

## Architecture Structure

### 1. User Types
- **VESSEL_OPERATOR**: Boat owners, yacht clubs, fleet managers who need charging services
- **POWER_OPERATOR**: Marina operators, admins who manage charging infrastructure

### 2. Folder Structure
```
frontend/src/
├── routes/
│   ├── vessel-operator/
│   │   ├── VesselOperatorRoutes.jsx
│   │   └── VesselOperatorSidebar.jsx
│   └── power-operator/
│       ├── PowerOperatorRoutes.jsx
│       └── PowerOperatorSidebar.jsx
├── pages/
│   ├── vessel-operator/
│   │   ├── VesselDashboard.jsx
│   │   ├── MyBookings.jsx
│   │   └── FindChargers.jsx
│   └── power-operator/
│       ├── PowerDashboard.jsx
│       ├── ManageStations.jsx
│       ├── ManageChargers.jsx
│       ├── BookingManagement.jsx
│       ├── Analytics.jsx
│       └── UserManagement.jsx
├── components/
│   └── shared/
│       ├── MapView.jsx
│       └── UserTypeIndicator.jsx
```

### 3. Route Configuration

#### Main App Router
The main `App.jsx` determines which route tree to load based on `user.type_name`:
- `POWER_OPERATOR` → PowerOperatorRoutes
- `VESSEL_OPERATOR` (default) → VesselOperatorRoutes

#### Vessel Operator Routes
- `/` - Dashboard (vessel-specific metrics)
- `/find-chargers` - Search and locate charging stations
- `/my-bookings` - Manage charging reservations
- `/my-vessels` - Vessel management
- `/stations` - Browse all stations

#### Power Operator Routes
- `/` - Dashboard (infrastructure metrics)
- `/stations` - Manage charging stations
- `/chargers` - Control individual chargers
- `/bookings` - Oversee all reservations
- `/analytics` - Performance insights
- `/users` - User account management

### 4. Shared Components
- **MapView**: Common map interface used by both user types
- **UserTypeIndicator**: Shows current user type context
- **UI Components**: All components from `/components/ui/` are shared

### 5. Navigation Differences

#### Vessel Operator Navigation
- Dashboard, Find Chargers, My Bookings, My Vessels, All Stations
- Blue color scheme
- Focus on finding and booking charging services

#### Power Operator Navigation
- Dashboard, Manage Stations, Manage Chargers, Booking Management, Analytics, User Management
- Green color scheme
- Focus on infrastructure management and business operations

## Benefits

### 1. Separation of Concerns
- Each user type has a dedicated application experience
- Different navigation, dashboards, and workflows
- Reduced cognitive load for users

### 2. Code Reuse
- Shared components (MapView, UI library, authentication)
- Common utilities and hooks
- Single backend API

### 3. Maintainability
- Clear folder structure
- Easy to add features for specific user types
- Isolated changes don't affect other user experiences

### 4. Scalability
- Easy to add new user types
- Can be extended to micro-frontend architecture
- Clear boundaries for team development

## Next Steps

### Phase 1: Enhanced Features
1. Implement booking flow for vessel operators
2. Add real-time charger status for power operators
3. Integrate analytics dashboard

### Phase 2: Advanced Functionality
1. Role-based permissions within user types
2. Multi-organization support
3. Advanced reporting and analytics

### Phase 3: Platform Expansion
1. Mobile-responsive optimizations
2. Progressive Web App features
3. Real-time notifications

## Implementation Notes

### Authentication Flow
1. User logs in through shared auth pages
2. Backend returns user data including `type_name`
3. Frontend routes to appropriate application view
4. Sidebar and navigation reflect user type context

### State Management
- AuthContext remains shared
- User type-specific state can be added as needed
- Shared state for common features (map, stations data)

### Component Sharing Strategy
- UI components are fully shared
- Business logic components shared where appropriate
- User type-specific components in respective folders
- Shared utilities in `/components/shared/`

This architecture provides a solid foundation for the dual-purpose AquaCharge application while maintaining efficient development and maintenance practices.