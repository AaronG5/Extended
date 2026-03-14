def normalize_voltage(raw: int) -> float:
   return (raw / 4096) * 250

def normalize_current(raw: int) -> float:
   return ((raw / 4096) * 40) - 20