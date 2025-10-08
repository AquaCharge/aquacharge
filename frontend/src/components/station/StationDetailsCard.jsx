import React from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { X } from 'lucide-react';

const StationDetailsCard = ({ station, onClose, onReserve }) => {
  const getAvailabilityStatus = () => {
    if (station.status !== 'active') return 'Under Maintenance';
    if (station.availableChargers === 0) return 'Fully Occupied';
    if (station.availableChargers === station.totalChargers) return 'All Available';
    return 'Limited Availability';
  };

  return (
    <Card className="border-0 shadow-xl">
      <CardHeader className="space-y-3 pb-4">
        <div className="flex items-start justify-between">
          <div className="space-y-1 flex-1">
            <CardTitle className="text-xl font-semibold leading-tight">
              {station.name}
            </CardTitle>
            <p className="text-sm text-muted-foreground">
              {getAvailabilityStatus()}
            </p>
          </div>
          <Button
            variant="ghost"
            size="icon"
            className="h-8 w-8 -mt-1 -mr-2"
            onClick={onClose}
          >
            <X className="h-4 w-4" />
          </Button>
        </div>
      </CardHeader>

      <CardContent className="space-y-6 pt-0">
        <div className="grid grid-cols-2 gap-4">
          <div className="space-y-1">
            <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
              Available
            </p>
            <p className="text-2xl font-bold">
              {station.availableChargers}
              <span className="text-base font-normal text-muted-foreground ml-1">
                of {station.totalChargers}
              </span>
            </p>
          </div>
          
          <div className="space-y-1">
            <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
              Status
            </p>
            <Badge 
              variant={station.status === 'active' ? 'default' : 'secondary'}
              className="text-xs font-medium"
            >
              {station.status}
            </Badge>
          </div>
        </div>

        <div className="space-y-2">
          <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
            Charger Types
          </p>
          <div className="flex flex-wrap gap-2">
            {station.chargerTypes.map((type, index) => (
              <span
                key={index}
                className="px-3 py-1 text-sm font-medium bg-secondary text-secondary-foreground rounded-md"
              >
                {type}
              </span>
            ))}
          </div>
        </div>

        <Button 
          className="w-full h-11 font-medium"
          disabled={station.availableChargers === 0 || station.status !== 'active'}
          onClick={() => onReserve && onReserve(station)}
        >
          Reserve Charging Slot
        </Button>
      </CardContent>
    </Card>
  );
};

export default StationDetailsCard;