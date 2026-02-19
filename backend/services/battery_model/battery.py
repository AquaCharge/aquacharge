"""
Class representing a Battery Energy Storage System (BESS) for a vessel, 
with methods to determine energy transfer based on charging/discharging decisions 
and to apply those transfers to the state of charge (SOC).
"""
class BESS:

    
    def __init__(self, vessel: dict):
        self.vessel_id       = vessel["id"]
        self.max             = float(vessel["capacity"])          # kWh (full capacity)
        self.min             = self.max * 0.20                    # kWh (20% SOC floor — safety threshold)
        self.soc             = float(vessel["currentSoc"])        # kWh (current stored energy)
        self.maxChargeRate   = float(vessel["maxChargeRate"])     # kW
        self.maxDischargeRate= float(vessel["maxDischargeRate"])  # kW


    def determine_energy_transfer(self, delta_t: float, decision: str) -> float:
        """
        Calculate energy transferred over delta_t hours.

        Args:
            delta_t:  Time interval in hours (e.g. 5/60 for 5 minutes)
            decision: "charge" | "discharge" | "idle"

        Returns:
            powerTransfer (kWh) — negative means energy left the battery
        """
        if decision == "charge":
            proposed = self.soc + (self.maxChargeRate * delta_t)
            transfer = (self.max - self.soc) if proposed > self.max else (proposed - self.soc)

        elif decision == "discharge":
            proposed = self.soc - (self.maxDischargeRate * delta_t)
            # Respect the SOC floor — never discharge below self.min
            if proposed < self.min:
                transfer = self.min - self.soc   # negative: drains only down to floor
            else:
                transfer = proposed - self.soc   # negative: normal discharge

        else:
            transfer = 0.0

        return transfer
    

    def apply_transfer(self, transfer: float):
        self.soc += transfer


    @property
    def at_floor(self) -> bool:
        return self.soc <= self.min