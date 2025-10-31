import React, { useState } from "react";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { X, Search, Filter } from "lucide-react";

const StationSearchFilters = ({
  stations = [],
  filters = {
    availableOnly: false,
    chargerTypes: [],
    maxDistance: null,
  },
  onStationSelect = () => {},
  onLocationSelect = () => {},
  onFilterChange = () => {},
}) => {
  const [searchQuery, setSearchQuery] = useState("");
  const [searchResults, setSearchResults] = useState([]);
  const [showResults, setShowResults] = useState(false);
  const [isSearching, setIsSearching] = useState(false);

  const handleSearch = async (query) => {
    setSearchQuery(query);

    if (!query.trim()) {
      setSearchResults([]);
      setShowResults(false);
      return;
    }

    setIsSearching(true);
    setShowResults(true);

    // Search in charging stations
    const stationResults = stations.filter((station) =>
      station.name.toLowerCase().includes(query.toLowerCase())
    );

    // Search for locations using Nominatim (OpenStreetMap geocoding)
    try {
      const response = await fetch(
        `https://nominatim.openstreetmap.org/search?format=json&q=${encodeURIComponent(
          query
        )}&limit=5`
      );
      const locationResults = await response.json();

      const combinedResults = [
        ...stationResults.map((station) => ({
          type: "station",
          data: station,
          display: station.name,
          subtitle: `${station.availableChargers} available`,
        })),
        ...locationResults.map((loc) => ({
          type: "location",
          data: loc,
          display: loc.display_name,
          subtitle: "Location",
        })),
      ];

      setSearchResults(combinedResults);
    } catch (error) {
      console.error("Search error:", error);
      setSearchResults(
        stationResults.map((station) => ({
          type: "station",
          data: station,
          display: station.name,
          subtitle: `${station.availableChargers} available`,
        }))
      );
    }

    setIsSearching(false);
  };

  const handleResultClick = (result) => {
    if (result.type === "station") {
      onStationSelect(result.data);
    } else {
      onLocationSelect({
        lat: parseFloat(result.data.lat),
        lon: parseFloat(result.data.lon),
      });
    }
    setShowResults(false);
    setSearchQuery("");
  };

  const clearSearch = () => {
    setSearchQuery("");
    setSearchResults([]);
    setShowResults(false);
  };

  const toggleFilter = (filterType, value = null) => {
    const newFilters = { ...filters };

    switch (filterType) {
      case "availableOnly":
        newFilters.availableOnly = !filters.availableOnly;
        break;
      case "chargerType":
        if (filters.chargerTypes.includes(value)) {
          newFilters.chargerTypes = filters.chargerTypes.filter(
            (t) => t !== value
          );
        } else {
          newFilters.chargerTypes = [...filters.chargerTypes, value];
        }
        break;
      case "distance":
        newFilters.maxDistance = filters.maxDistance === value ? null : value;
        break;
      default:
        break;
    }

    onFilterChange(newFilters);
  };

  const isFilterActive = (filterType, value = null) => {
    switch (filterType) {
      case "availableOnly":
        return filters.availableOnly;
      case "chargerType":
        return filters.chargerTypes.includes(value);
      case "distance":
        return filters.maxDistance === value;
      default:
        return false;
    }
  };

  return (
    <div className="bg-background border-b py-3 space-y-3">
      <div className="flex gap-2">
        {/* Search Bar */}
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <Input
            type="text"
            placeholder="Search stations or locations..."
            value={searchQuery}
            onChange={(e) => handleSearch(e.target.value)}
            className="pl-10 pr-10"
          />
          {searchQuery && (
            <Button
              variant="ghost"
              size="icon"
              className="absolute right-1 top-1/2 transform -translate-y-1/2 h-7 w-7"
              onClick={clearSearch}
            >
              <X className="h-4 w-4" />
            </Button>
          )}

          {/* Search Results Dropdown */}
          {showResults && searchResults.length > 0 && (
            <Card className="absolute top-full mt-2 w-full shadow-xl border z-[3000] max-h-80 overflow-y-auto">
              <CardContent className="p-0">
                {searchResults.map((result, index) => (
                  <button
                    key={index}
                    onClick={() => handleResultClick(result)}
                    className="w-full px-4 py-3 text-left hover:bg-accent transition-colors border-b last:border-b-0 flex items-start gap-3"
                  >
                    <div className="flex-1 min-w-0">
                      <p className="font-medium text-sm truncate">
                        {result.display}
                      </p>
                      <p className="text-xs text-muted-foreground truncate">
                        {result.subtitle}
                      </p>
                    </div>
                    {result.type === "station" && (
                      <Badge variant="outline" className="text-xs shrink-0">
                        Station
                      </Badge>
                    )}
                  </button>
                ))}
              </CardContent>
            </Card>
          )}

          {showResults &&
            searchResults.length === 0 &&
            !isSearching &&
            searchQuery && (
              <Card className="absolute top-full mt-2 w-full shadow-xl border z-50">
                <CardContent className="p-4">
                  <p className="text-sm text-muted-foreground text-center">
                    No results found
                  </p>
                </CardContent>
              </Card>
            )}
        </div>

        {/* Filter Button */}
        <Button variant="outline" size="icon">
          <Filter className="h-4 w-4" />
        </Button>
      </div>

      {/* Filter Chips */}
      <div className="flex flex-wrap gap-2">
        <Button
          variant={isFilterActive("availableOnly") ? "default" : "outline"}
          size="sm"
          className="h-8 rounded-full"
          onClick={() => toggleFilter("availableOnly")}
        >
          Available Only
        </Button>
        <Button
          variant={
            isFilterActive("chargerType", "Type 2") ? "default" : "outline"
          }
          size="sm"
          className="h-8 rounded-full"
          onClick={() => toggleFilter("chargerType", "Type 2")}
        >
          Type 2
        </Button>
        <Button
          variant={isFilterActive("chargerType", "CCS") ? "default" : "outline"}
          size="sm"
          className="h-8 rounded-full"
          onClick={() => toggleFilter("chargerType", "CCS")}
        >
          CCS
        </Button>
        <Button
          variant={
            isFilterActive("chargerType", "CHAdeMO") ? "default" : "outline"
          }
          size="sm"
          className="h-8 rounded-full"
          onClick={() => toggleFilter("chargerType", "CHAdeMO")}
        >
          CHAdeMO
        </Button>
        <Button
          variant={isFilterActive("distance", 5) ? "default" : "outline"}
          size="sm"
          className="h-8 rounded-full"
          onClick={() => toggleFilter("distance", 5)}
        >
          Within 5km
        </Button>
      </div>
    </div>
  );
};

export default StationSearchFilters;
