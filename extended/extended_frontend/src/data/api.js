const BASE = 'http://stavaris.com/api';

// ── Raw fetches ──────────────────────────────────────────────────────────────

async function get(path) {
  const res = await fetch(`${BASE}${path}`);
  if (!res.ok) throw new Error(`API ${path} → ${res.status}`);
  return res.json();
}

export const getDeviceIds  = ()      => get('/devices/');
export const getDashboard  = (espId) => get(`/dashboard/${espId}/`);

// ── Shape mapping ────────────────────────────────────────────────────────────

function capitalize(str) {
  if (!str) return str;
  return str.charAt(0).toUpperCase() + str.slice(1);
}

/**
 * Maps one dashboard response into the array of device objects that
 * DeviceCard and PowerExtenderSVG expect.
 */
export function mapDashboard(dashboard) {
  return dashboard.outlets.map(outlet => ({
    id:               `${dashboard.esp32_id}-${outlet.outlet_index}`,
    esp32Id:          dashboard.esp32_id,
    slot:             outlet.outlet_index + 1,          // 1-indexed
    name:             capitalize(outlet.device_type) ?? `Slot ${outlet.outlet_index + 1}`,
    pluggedIn:        outlet.device_type !== null,
    buttonState:      outlet.button_state,
    currentPowerDraw: outlet.wattage,
    kwhRecorded:      outlet.kwh_recorded,
    hasAlert:         false,  // no alert field in API yet
    alertMessage:     null,
  }));
}

// ── Outlet readings (graph data) ─────────────────────────────────────────────

const LT_TO_API_PERIOD = {
  valanda: 'hour',
  diena:   'day',
  'savaitė': 'week',
  'mėnesis': 'month',
};

function formatTimestamp(iso, period) {
  const d = new Date(iso);
  if (period === 'week') {
    return d.toLocaleDateString('lt-LT', { weekday: 'short', month: 'numeric', day: 'numeric' });
  }
  return d.toLocaleTimeString('lt-LT', { hour: '2-digit', minute: '2-digit' });
}

/**
 * Fetches wattage readings for one outlet and maps them to { time, watts }
 * ready for the recharts LineChart in DeviceCard.
 *
 * @param {string} espId        — e.g. "ABC123"
 * @param {number} outletIndex  — 0-based
 * @param {string} ltPeriod     — 'valanda' | 'diena' | 'savaitė'
 */
export async function fetchOutletReadings(espId, outletIndex, ltPeriod) {
  const period = LT_TO_API_PERIOD[ltPeriod] ?? 'day';
  const data = await get(`/outlet/${espId}/readings/?outlet_index=${outletIndex}&period=${period}`);
  return data.map(r => ({
    time:  formatTimestamp(r.timestamp, period),
    watts: r.wattage,
  }));
}

// ── Energy breakdown (pie chart) ─────────────────────────────────────────────

/**
 * Fetches kWh breakdown per device type for one extender.
 * Maps null device_type to "Nežinoma".
 *
 * @param {string} espId    — e.g. "ABC123"
 * @param {string} ltPeriod — 'diena' | 'savaitė' | 'mėnesis'
 * @returns {Array<{ name, kwh }>}
 */
async function fetchEnergyByDevice(espId, ltPeriod) {
  const period = LT_TO_API_PERIOD[ltPeriod] ?? 'day';
  const data = await get(`/energy/${espId}/?period=${period}`);
  return data.map(row => ({
    name: row.device_type
      ? capitalize(row.device_type.replace(/_/g, ' '))
      : 'Nežinoma',
    kwh: row.kwh,
  }));
}

/**
 * Fetches and aggregates energy across ALL extenders, merging slices
 * with the same device name by summing their kWh.
 *
 * @param {string} ltPeriod — 'diena' | 'savaitė' | 'mėnesis'
 * @returns {Array<{ name, kwh }>}
 */
export async function fetchAllEnergyByDevice(ltPeriod) {
  const { devices: espIds } = await getDeviceIds();
  const perExtender = await Promise.all(espIds.map(id => fetchEnergyByDevice(id, ltPeriod)));
  const flat = perExtender.flat();

  // Merge duplicate device names
  const merged = {};
  flat.forEach(({ name, kwh }) => {
    merged[name] = (merged[name] ?? 0) + kwh;
  });
  return Object.entries(merged).map(([name, kwh]) => ({
    name,
    kwh: parseFloat(kwh.toFixed(4)),
  }));
}

// ── High-level helpers used by pages ─────────────────────────────────────────

/**
 * Returns an array of { espId, devices[] } — one entry per extender.
 * Each devices[] entry is ready for DeviceCard / PowerExtenderSVG.
 */
export async function fetchAllExtenders() {
  const { devices: espIds } = await getDeviceIds();
  const dashboards = await Promise.all(espIds.map(id => getDashboard(id)));
  return dashboards.map(dash => ({
    espId:   dash.esp32_id,
    devices: mapDashboard(dash),
  }));
}
