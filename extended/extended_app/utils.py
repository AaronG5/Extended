def normalize_voltage(raw: int) -> float:
   return ((raw / 4096) * 500) - 250

def normalize_current(raw: int) -> float:
   return ((raw / 4096) * 40) - 20

def abs_wattage(voltage: float, current: float) -> float:
   return abs(voltage * current)