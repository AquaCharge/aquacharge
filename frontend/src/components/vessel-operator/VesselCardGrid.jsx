// Replace your existing vessel card grid with this component.
// Assumes vessels prop is passed in with the Vessel model shape.
// Requires: shadcn Card/Badge, lucide-react Ship icon, and a useState import.

import { useState } from "react";
import { Ship, Zap, Anchor, Route, BatteryCharging, ChevronRight } from "lucide-react";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";

// --- DynamoDB type normalizer ---
// DynamoDB can return numbers as strings. This coerces all numeric fields
// on the Vessel model so .toFixed() and arithmetic never throw.
function parseVessel(v) {
  const capacity = parseFloat(v.capacity) || 0
  const maxCapacity = parseFloat(v.maxCapacity) || 0
  const explicitSoc = parseFloat(v.currentSoc ?? v.soc)
  const derivedSoc = maxCapacity > 0 ? (capacity / maxCapacity) * 100 : 0
  const resolvedSoc = Number.isFinite(explicitSoc)
    ? explicitSoc
    : Math.max(0, Math.min(100, derivedSoc))
  const currentChargeKwh = maxCapacity > 0
    ? (maxCapacity * resolvedSoc) / 100
    : capacity

  return {
    ...v,
    capacity: currentChargeKwh,
    maxCapacity,
    maxChargeRate:    parseFloat(v.maxChargeRate)     || 0,
    minChargeRate:    parseFloat(v.minChargeRate)     || 0,
    maxDischargeRate: parseFloat(v.maxDischargeRate)  || 0,
    rangeMeters:      parseFloat(v.rangeMeters)       || 0,
    latitude:         parseFloat(v.latitude)          || 0,
    longitude:        parseFloat(v.longitude)         || 0,
    soc:              resolvedSoc,
  };
}

// --- Helpers ---

const TYPE_COLOR = {
  Container: { pill: "bg-blue-50 text-blue-700 border-blue-200",   accent: "text-blue-600",  bar: "bg-blue-500"  },
  Ferry:     { pill: "bg-purple-50 text-purple-700 border-purple-200", accent: "text-purple-600", bar: "bg-purple-500" },
  Tanker:    { pill: "bg-amber-50 text-amber-700 border-amber-200",  accent: "text-amber-600", bar: "bg-amber-500"  },
  Cargo:     { pill: "bg-emerald-50 text-emerald-700 border-emerald-200", accent: "text-emerald-600", bar: "bg-emerald-500" },
};

function getSocColor(soc, active) {
  if (!active) return { text: "text-gray-400", bar: "bg-gray-300" };
  if (soc > 70)  return { text: "text-green-600",  bar: "bg-green-500"  };
  if (soc > 35)  return { text: "text-amber-600",  bar: "bg-amber-500"  };
  return           { text: "text-red-600",    bar: "bg-red-500"    };
}

function SocBar({ soc, active }) {
  const { text, bar } = getSocColor(soc, active);
  return (
    <div className="space-y-1.5">
      <div className="flex justify-between items-center">
        <span className="text-xs text-muted-foreground">State of Charge</span>
        <span className={`text-xs font-bold ${text}`}>{active ? `${soc}%` : "—"}</span>
      </div>
      <div className="h-1.5 w-full bg-gray-100 rounded-full overflow-hidden">
        <div
          className={`h-full rounded-full transition-all duration-500 ${bar}`}
          style={{ width: active ? `${soc}%` : "0%" }}
        />
      </div>
    </div>
  );
}

// --- Detail Modal ---

function DetailPanel({ vessel, onClose }) {
  if (!vessel) return null;
  const typeStyle = TYPE_COLOR[vessel.vesselType] || { pill: "", accent: "text-gray-500", bar: "bg-gray-400" };
  const { text: socText, bar: socBar } = getSocColor(vessel.soc, vessel.active);

  const rows = [
    ["Vessel ID",           <span className="font-mono text-xs break-all">{vessel.id}</span>],
    ["Vessel Type",         vessel.vesselType],
    ["Charger Type",        vessel.chargerType],
    ["Battery Capacity",    `${vessel.maxCapacity.toFixed(1)} kWh`],
    ["Current Charge",      `${vessel.capacity.toFixed(1)} kWh`],
    ["Max Charge Rate",     `${vessel.maxChargeRate} kW`],
    ["Min Charge Rate",     `${vessel.minChargeRate} kW`],
    ["Max Discharge Rate",  `${vessel.maxDischargeRate} kW`],
    ["Range (Full Charge)", `${(vessel.rangeMeters / 1000).toFixed(0)} km`],
    ["Latitude",            vessel.latitude.toFixed(5)],
    ["Longitude",           vessel.longitude.toFixed(5)],
    ["Created",             vessel.createdAt],
    ["Last Updated",        vessel.updatedAt ?? "—"],
  ];

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-6 bg-black/40 backdrop-blur-sm"
      onClick={onClose}
    >
      <div
        className="bg-white rounded-2xl shadow-2xl w-full max-w-md max-h-[90vh] overflow-y-auto"
        onClick={e => e.stopPropagation()}
      >
        <div className="p-7">
          {/* Header */}
          <div className="flex items-start justify-between mb-5">
            <div className="flex items-center gap-3">
              <div className={`w-11 h-11 rounded-xl flex items-center justify-center bg-gray-50 border`}>
                <Ship className={`h-5 w-5 ${typeStyle.accent}`} />
              </div>
              <div>
                <h2 className="text-lg font-bold text-gray-900">{vessel.displayName}</h2>
                <div className="flex gap-2 mt-1.5 flex-wrap">
                  <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-semibold border ${typeStyle.pill}`}>
                    {vessel.vesselType}
                  </span>
                  <Badge variant={vessel.active ? "default" : "secondary"} className="text-xs">
                    {vessel.active ? "Active" : "Offline"}
                  </Badge>
                </div>
              </div>
            </div>
            <button
              onClick={onClose}
              className="text-gray-400 hover:text-gray-600 transition-colors text-xl leading-none mt-0.5"
            >
              ✕
            </button>
          </div>

          {/* SOC */}
          <div className="bg-gray-50 rounded-xl p-4 mb-5">
            <div className="flex justify-between items-center mb-2">
              <span className="text-sm font-semibold text-gray-700">State of Charge</span>
              <span className={`text-2xl font-extrabold ${socText}`}>{vessel.active ? `${vessel.soc}%` : "—"}</span>
            </div>
            <div className="h-2 w-full bg-gray-200 rounded-full overflow-hidden">
              <div className={`h-full rounded-full ${socBar}`} style={{ width: vessel.active ? `${vessel.soc}%` : "0%" }} />
            </div>
            {vessel.active && (
              <p className="text-xs text-muted-foreground mt-2">
                {vessel.soc > 50
                  ? "✓ Eligible for DR event participation"
                  : "✗ SOC below 50% — not eligible for DR events"}
              </p>
            )}
          </div>

          {/* Details table */}
          <div className="border border-gray-100 rounded-xl overflow-hidden mb-5">
            {rows.map(([label, value], i) => (
              <div
                key={label}
                className={`flex justify-between items-start gap-4 px-4 py-2.5 text-sm ${i % 2 === 0 ? "bg-white" : "bg-gray-50"} ${i < rows.length - 1 ? "border-b border-gray-50" : ""}`}
              >
                <span className="text-muted-foreground shrink-0">{label}</span>
                <span className="font-semibold text-gray-900 text-right">{value}</span>
              </div>
            ))}
          </div>

          {/* Actions */}
          <div className="flex gap-3">
            <button className="flex-1 py-2.5 rounded-lg border border-gray-200 text-sm font-semibold text-gray-700 hover:bg-gray-50 transition-colors">
              Edit Vessel
            </button>
            <button className="flex-1 py-2.5 rounded-lg bg-gray-900 text-sm font-semibold text-white hover:bg-gray-800 transition-colors">
              Book Charger
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

// --- Vessel Card ---

function VesselCard({ vessel, onSelect }) {
  const typeStyle = TYPE_COLOR[vessel.vesselType] || { pill: "", accent: "text-gray-500" };

  return (
    <Card
      className="hover:shadow-md transition-all duration-150 cursor-pointer group"
      onClick={() => onSelect(vessel)}
    >
      <CardHeader className="pb-3">
        {/* Name row */}
        <div className="flex items-start justify-between gap-3">
          <div className="flex items-center gap-2 min-w-0">
            <Ship className={`h-4 w-4 shrink-0 ${typeStyle.accent}`} />
            <span className="font-bold text-gray-900 truncate">{vessel.displayName}</span>
          </div>
          <ChevronRight className="h-4 w-4 text-gray-300 shrink-0 group-hover:text-gray-500 transition-colors mt-0.5" />
        </div>

        {/* ID + pills */}
        <div className="flex items-center justify-between gap-2 mt-1.5">
          <div className="flex gap-1.5 flex-wrap justify-end">
            <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-semibold border ${typeStyle.pill}`}>
              {vessel.vesselType}
            </span>
            <Badge variant={vessel.active ? "default" : "secondary"} className="text-xs">
              {vessel.active ? "Active" : "Offline"}
            </Badge>
          </div>
        </div>
      </CardHeader>

      <CardContent className="space-y-3">
        {/* Metrics grid */}
        <div className="grid grid-cols-2 gap-x-4 gap-y-2.5">
          <div>
            <p className="text-xs text-muted-foreground mb-0.5">Battery Capacity</p>
            <p className="text-sm font-semibold text-gray-800">{vessel.maxCapacity.toFixed(1)} kWh</p>
          </div>
          <div>
            <p className="text-xs text-muted-foreground mb-0.5">Range</p>
            <p className="text-sm font-semibold text-gray-800">{(vessel.rangeMeters / 1000).toFixed(0)} km</p>
          </div>
          <div>
            <p className="text-xs text-muted-foreground mb-0.5">Max Discharge</p>
            <p className="text-sm font-semibold text-gray-800">{vessel.maxDischargeRate.toFixed(1)} kW</p>
          </div>
          <div>
            <p className="text-xs text-muted-foreground mb-0.5">Charger Type</p>
            <p className="text-sm font-semibold text-gray-800">{vessel.chargerType}</p>
          </div>
        </div>

        <div className="border-t pt-3">
          <SocBar soc={vessel.soc} active={vessel.active} />
        </div>
      </CardContent>
    </Card>
  );
}

// --- Main export: drop-in replacement for your card grid ---

export function VesselCardGrid({ vessels = [] }) {
  const [selected, setSelected] = useState(null);
  const parsed = vessels.map(parseVessel);
  return (
    <>
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        {parsed.map((vessel) => (
          <VesselCard key={vessel.id} vessel={vessel} onSelect={setSelected} />
        ))}
      </div>

      <DetailPanel vessel={selected} onClose={() => setSelected(null)} />
    </>
  );
}
