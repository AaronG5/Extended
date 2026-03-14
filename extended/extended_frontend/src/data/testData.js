// Mock data — replace each fetchX() body with a real fetch() call when the API is ready.

const _devices = [
  { id: 1, name: 'Gaming PC',    slot: 1, pluggedIn: true,  hasAlert: false, alertMessage: null,                          currentPowerDraw: 245 },
  { id: 2, name: 'Monitor',      slot: 2, pluggedIn: true,  hasAlert: false, alertMessage: null,                          currentPowerDraw: 38  },
  { id: 3, name: 'Space Heater', slot: 3, pluggedIn: true,  hasAlert: true,  alertMessage: 'High consumption detected',   currentPowerDraw: 1800 },
  { id: 4, name: 'Lamp',         slot: null, pluggedIn: false, hasAlert: false, alertMessage: null,                       currentPowerDraw: 0   },
  { id: 5, name: 'Old Printe1r',  slot: null, pluggedIn: false, hasAlert: false, alertMessage: null,                       currentPowerDraw: 0   },
  { id: 6, name: 'Coffee Maker', slot: null, pluggedIn: false, hasAlert: false, alertMessage: null,                       currentPowerDraw: 0   },
];

const _powerHistory = {};
[1, 2, 3, 4, 5, 6].forEach(id => {
  const base = _devices.find(d => d.id === id)?.currentPowerDraw || 50;
  _powerHistory[id] = {
    hour: Array.from({ length: 60 }, (_, i) => ({
      time: `${i}m`,
      watts: Math.max(0, base + Math.sin(i / 5) * base * 0.15 + (Math.random() - 0.5) * base * 0.05),
    })),
    day: Array.from({ length: 24 }, (_, i) => ({
      time: `${i}:00`,
      watts: Math.max(0, base + Math.sin(i / 4) * base * 0.2 + (Math.random() - 0.5) * base * 0.05),
    })),
    week: Array.from({ length: 7 }, (_, i) => ({
      time: ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'][i],
      watts: Math.max(0, base + Math.sin(i / 2) * base * 0.25),
    })),
  };
});

const _energyPrices = Array.from({ length: 48 }, (_, i) => ({
  time: `${String(Math.floor(i / 2)).padStart(2, '0')}:${i % 2 === 0 ? '00' : '30'}`,
  price: parseFloat((0.12 + 0.05 * Math.sin((i / 48) * 2 * Math.PI) + 0.01 * Math.sin((i / 12) * 2 * Math.PI)).toFixed(4)),
}));

const _standbyPower = 23;

const _alerts = [
  { id: 1, deviceId: 3, deviceName: 'Space Heater', message: 'High consumption detected (1800W)', timestamp: '2026-03-14T08:23:00', severity: 'warning' },
  { id: 2, deviceId: 1, deviceName: 'Gaming PC',    message: 'Power spike detected (+40% above average)', timestamp: '2026-03-13T22:11:00', severity: 'info' },
  { id: 3, deviceId: 2, deviceName: 'Monitor',      message: 'Voltage spike: 248V detected (threshold 240V)', timestamp: '2026-03-14T06:47:00', severity: 'warning' },
];

// --- API-shaped exports ---

export const fetchDevices = () => Promise.resolve([..._devices]);

export const fetchPowerHistory = (deviceId, granularity = 'day') =>
  Promise.resolve((_powerHistory[deviceId]?.[granularity] ?? []).map(p => ({ ...p, watts: parseFloat(p.watts.toFixed(1)) })));

export const fetchEnergyPrices = () => Promise.resolve([..._energyPrices]);

export const fetchStandbyPower = () => Promise.resolve(_standbyPower);

export const fetchAlerts = () => Promise.resolve([..._alerts]);

export const fetchDeviceKwh = (period = 'day') => {
  const hours = period === 'day' ? 24 : period === 'week' ? 168 : 720;
  return Promise.resolve(
    _devices.map(d => ({
      id: d.id,
      name: d.name,
      kwh: parseFloat((d.currentPowerDraw * hours / 1000).toFixed(2)),
    }))
  );
};
