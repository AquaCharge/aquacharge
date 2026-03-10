"""
Class representing a Battery Energy Storage System (BESS) for a vessel,
with methods to determine energy transfer based on charging/discharging decisions
and to apply those transfers to the state of charge (SOC).
"""


class BESS:
    def __init__(self, vessel: dict):
        self.vessel_id = vessel["id"]
        # `maxCapacity` is the full battery capacity in kWh; `capacity` is current stored kWh
        self.max = float(vessel.get("maxCapacity") or 0.0)  # kWh (full capacity)
        self.min = self.max * 0.20  # kWh (20% SOC floor - safety threshold)
        self.soc = float(vessel.get("capacity") or 0.0)  # kWh (current stored energy)
        self.maxChargeRate = float(vessel.get("maxChargeRate") or 0.0)  # kW
        self.maxDischargeRate = float(vessel.get("maxDischargeRate") or 0.0)  # kW

    @property
    def soc_percent(self) -> float:
        if self.max <= 0:
            return 0.0
        return (self.soc / self.max) * 100.0

    def determine_energy_transfer(self, delta_t: float, decision: str) -> float:
        """
        Calculate energy transferred over delta_t hours.

        Args:
            delta_t:  Time interval in hours (e.g. 5/60 for 5 minutes)
            decision: "charge" | "discharge" | "idle"

        Returns:
            powerTransfer (kWh) - negative means energy left the battery
        """
        if decision == "charge":
            proposed = self.soc + (self.maxChargeRate * delta_t)
            transfer = (
                (self.max - self.soc) if proposed > self.max else (proposed - self.soc)
            )

        elif decision == "discharge":
            proposed = self.soc - (self.maxDischargeRate * delta_t)
            # Respect the SOC floor - never discharge below self.min
            if proposed < self.min:
                transfer = self.min - self.soc  # negative: drains only down to floor
            else:
                transfer = proposed - self.soc  # negative: normal discharge

        else:
            transfer = 0.0

        return transfer

    def apply_transfer(self, transfer: float):
        self.soc += transfer

    @property
    def at_floor(self) -> bool:
        return self.soc <= self.min
