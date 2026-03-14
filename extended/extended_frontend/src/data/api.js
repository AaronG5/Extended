const BASE = '/api';

// ── Raw fetches ──────────────────────────────────────────────────────────────

async function get(path) {
  const url = `${BASE}${path}`;
  console.log(`[api] GET ${url}`);
  let res;
  try {
    res = await fetch(url);
  } catch (err) {
    console.error(`[api] GET ${url} — network error:`, err);
    throw err;
  }
  console.log(`[api] GET ${url} → ${res.status} ${res.statusText}`);
  if (!res.ok) {
    const text = await res.text().catch(() => '');
    console.error(`[api] GET ${url} — error body:`, text);
    throw new Error(`API ${path} → ${res.status}`);
  }
  const json = await res.json();
  console.log(`[api] GET ${url} — response:`, json);
  return json;
}

export const getDeviceIds  = ()      => get('/devices/');
export const getDashboard  = (espId) => get(`/dashboard/${espId}/`);

async function post(path, body) {
  const url = `${BASE}${path}`;
  console.log(`[api] POST ${url}`, body);
  let res;
  try {
    res = await fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
  } catch (err) {
    console.error(`[api] POST ${url} — network error:`, err);
    throw err;
  }
  console.log(`[api] POST ${url} → ${res.status} ${res.statusText}`);
  if (!res.ok) {
    const text = await res.text().catch(() => '');
    console.error(`[api] POST ${url} — error body:`, text);
    throw new Error(`API ${path} → ${res.status}`);
  }
  const json = await res.json();
  console.log(`[api] POST ${url} — response:`, json);
  return json;
}

async function classifyOutlet(espId, outletIndex) {
  const result = await post('/classify-latest/', { esp32_id: espId, outlet_index: outletIndex });
  return result; // { device_guess, probability, ... }
}

// ── Shape mapping ────────────────────────────────────────────────────────────

function capitalize(str) {
  if (!str) return str;
  return str.charAt(0).toUpperCase() + str.slice(1);
}

/**
 * Maps one dashboard response into the array of device objects that
 * DeviceCard and PowerExtenderSVG expect.
 */
// guesses: Map of outlet_index → { device_guess, probability }
export function mapDashboard(dashboard, guesses = {}) {
  console.log(`[api] mapDashboard esp32_id=${dashboard.esp32_id}`, dashboard);
  return dashboard.outlets.map(outlet => {
    const guess = guesses[outlet.outlet_index];
    const name = guess
      ? capitalize(guess.device_guess)
      : capitalize(outlet.device_type) ?? `Slot ${outlet.outlet_index + 1}`;
    return {
      id:               `${dashboard.esp32_id}-${outlet.outlet_index}`,
      esp32Id:          dashboard.esp32_id,
      slot:             outlet.outlet_index + 1,
      name,
      deviceGuess:      guess?.device_guess ?? null,
      guessProbability: guess?.probability ?? null,
      pluggedIn:        outlet.device_type !== null,
      buttonState:      outlet.button_state,
      currentPowerDraw: outlet.wattage,
      kwhRecorded:      outlet.kwh_recorded,
      hasAlert:         false,
      alertMessage:     null,
    };
  });
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
  console.log(`[api] fetchOutletReadings esp=${espId} outlet=${outletIndex} period=${period}`);
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
  console.log(`[api] fetchEnergyByDevice esp=${espId} period=${period}`);
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
  console.log(`[api] fetchAllEnergyByDevice period=${ltPeriod}`);
  const { devices: espIds } = await getDeviceIds();
  console.log(`[api] fetchAllEnergyByDevice espIds:`, espIds);
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
  console.log('[api] fetchAllExtenders — start');
  const { devices: espIds } = await getDeviceIds();
  console.log('[api] fetchAllExtenders — espIds:', espIds);
  const dashboards = await Promise.all(espIds.map(id => getDashboard(id)));
  console.log('[api] fetchAllExtenders — dashboards:', dashboards);

  // Classify all outlets with button_state=true in parallel
  const result = await Promise.all(dashboards.map(async dash => {
    const activeOutlets = dash.outlets.filter(o => o.button_state === true);
    console.log(`[api] fetchAllExtenders — classifying ${activeOutlets.length} active outlet(s) for ${dash.esp32_id}`);

    const classifications = await Promise.all(
      activeOutlets.map(o =>
        classifyOutlet(dash.esp32_id, o.outlet_index)
          .then(r => ({ outletIndex: o.outlet_index, ...r }))
          .catch(err => {
            console.warn(`[api] classify failed for ${dash.esp32_id}[${o.outlet_index}]:`, err);
            return null;
          })
      )
    );

    const guesses = {};
    classifications.forEach(c => {
      if (c) guesses[c.outletIndex] = c;
    });
    console.log(`[api] fetchAllExtenders — guesses for ${dash.esp32_id}:`, guesses);

    return {
      espId:   dash.esp32_id,
      devices: mapDashboard(dash, guesses),
    };
  }));

  console.log('[api] fetchAllExtenders — result:', result);
  return result;
}

/**
 * Fetches anomalies from all extender dashboards and returns a flat,
 * sorted array ready for the Alerts card.
 * @returns {Array<{ id, outletId, espId, type, message, timestamp }>}
 */
export async function fetchAlerts() {
  console.log('[api] fetchAlerts — start');
  const { devices: espIds } = await getDeviceIds();
  const dashboards = await Promise.all(espIds.map(id => getDashboard(id)));

  const alerts = dashboards.flatMap(dash =>
    (dash.anomalies ?? []).map(a => ({
      id:        `${dash.esp32_id}-${a.outlet_id}-${a.timestamp}`,
      outletId:  a.outlet_id,
      espId:     dash.esp32_id,
      type:      a.type,
      message:   a.message,
      timestamp: a.timestamp,
    }))
  );

  alerts.sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp));
  console.log('[api] fetchAlerts — alerts:', alerts);
  return alerts;
}
