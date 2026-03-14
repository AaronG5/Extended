const BASE = 'mock://stavaris.com/api';
let requestCounter = 0;

const MOCK_DEVICE_IDS = ['ESP32-A1', 'ESP32-B2'];

const MOCK_DASHBOARDS = {
  'ESP32-A1': {
    esp32_id: 'ESP32-A1',
    outlets: [
      { outlet_index: 0, device_type: 'gaming_pc', button_state: true, wattage: 243.4, kwh_recorded: 12.7421 },
      { outlet_index: 1, device_type: 'monitor', button_state: true, wattage: 38.2, kwh_recorded: 2.1189 },
      { outlet_index: 2, device_type: 'space_heater', button_state: true, wattage: 1812.7, kwh_recorded: 36.0422 },
      { outlet_index: 3, device_type: null, button_state: false, wattage: 0, kwh_recorded: 0.0 },
    ],
  },
  'ESP32-B2': {
    esp32_id: 'ESP32-B2',
    outlets: [
      { outlet_index: 0, device_type: 'router', button_state: true, wattage: 12.6, kwh_recorded: 1.4205 },
      { outlet_index: 1, device_type: 'desk_lamp', button_state: true, wattage: 9.3, kwh_recorded: 0.8099 },
      { outlet_index: 2, device_type: 'coffee_maker', button_state: false, wattage: 0, kwh_recorded: 4.2291 },
      { outlet_index: 3, device_type: null, button_state: false, wattage: 0, kwh_recorded: 0.0 },
    ],
  },
};

function sleep(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}

function cloneJson(data) {
  return JSON.parse(JSON.stringify(data));
}

function pseudoNoise(seed) {
  return Math.sin(seed * 12.9898) * 43758.5453 % 1;
}

function generateReadings(espId, outletIndex, period) {
  const outlet = MOCK_DASHBOARDS[espId]?.outlets?.[outletIndex];
  const base = outlet?.wattage ?? 0;
  const now = new Date();

  const stepByPeriod = {
    hour: { points: 60, minutesStep: 1 },
    day: { points: 24, minutesStep: 60 },
    week: { points: 7, minutesStep: 60 * 24 },
  };

  const cfg = stepByPeriod[period] ?? stepByPeriod.day;

  return Array.from({ length: cfg.points }, (_, idx) => {
    const reverseIdx = cfg.points - idx - 1;
    const timestamp = new Date(now.getTime() - reverseIdx * cfg.minutesStep * 60 * 1000).toISOString();

    if (!base) {
      return { timestamp, wattage: 0 };
    }

    const wave = Math.sin(idx / 4) * base * 0.14;
    const jitter = pseudoNoise(idx + outletIndex * 17) * base * 0.06;
    const wattage = Math.max(0, base + wave + jitter);
    return { timestamp, wattage: parseFloat(wattage.toFixed(2)) };
  });
}

function periodFactor(period) {
  if (period === 'week') return 7;
  if (period === 'month') return 30;
  return 1;
}

function resolveMockGet(path) {
  const parsed = new URL(`${BASE}${path}`);
  const pathname = parsed.pathname;

  if (pathname === '/api/devices/') {
    return { devices: MOCK_DEVICE_IDS };
  }

  const dashboardMatch = pathname.match(/^\/api\/dashboard\/([^/]+)\/$/);
  if (dashboardMatch) {
    const espId = dashboardMatch[1];
    const dashboard = MOCK_DASHBOARDS[espId];
    if (!dashboard) {
      throw new Error(`API ${path} -> 404`);
    }
    return dashboard;
  }

  const outletReadingsMatch = pathname.match(/^\/api\/outlet\/([^/]+)\/readings\/$/);
  if (outletReadingsMatch) {
    const espId = outletReadingsMatch[1];
    const outletIndex = Number(parsed.searchParams.get('outlet_index') ?? '0');
    const period = parsed.searchParams.get('period') ?? 'day';
    return generateReadings(espId, outletIndex, period);
  }

  const energyMatch = pathname.match(/^\/api\/energy\/([^/]+)\/$/);
  if (energyMatch) {
    const espId = energyMatch[1];
    const period = parsed.searchParams.get('period') ?? 'day';
    const dashboard = MOCK_DASHBOARDS[espId];
    if (!dashboard) {
      throw new Error(`API ${path} -> 404`);
    }

    const rows = dashboard.outlets
      .filter(o => o.device_type)
      .map(o => ({
        device_type: o.device_type,
        kwh: parseFloat((o.kwh_recorded * periodFactor(period)).toFixed(4)),
      }));

    return rows;
  }

  throw new Error(`API ${path} -> 404`);
}

// ── Raw fetches ──────────────────────────────────────────────────────────────

async function get(path) {
  const requestId = ++requestCounter;
  const url = `${BASE}${path}`;
  const startedAt = performance.now();

  console.groupCollapsed(`[API][GET][${requestId}] ${path}`);
  console.log('Request', {
    id: requestId,
    method: 'GET',
    path,
    url,
    startedAtIso: new Date().toISOString(),
  });

  try {
    await sleep(120);
    const data = resolveMockGet(path);
    const elapsedMs = Math.round(performance.now() - startedAt);

    console.log('Response metadata', {
      id: requestId,
      ok: true,
      status: 200,
      statusText: 'OK (mock)',
      elapsedMs,
      headers: {},
      source: 'mock-data',
    });

    console.log('Response payload', {
      id: requestId,
      payloadType: Array.isArray(data) ? 'array' : typeof data,
      itemCount: Array.isArray(data) ? data.length : undefined,
      payload: data,
    });

    return cloneJson(data);
  } catch (error) {
    const elapsedMs = Math.round(performance.now() - startedAt);
    console.error('GET exception', {
      id: requestId,
      path,
      url,
      elapsedMs,
      message: error instanceof Error ? error.message : String(error),
      stack: error instanceof Error ? error.stack : undefined,
    });
    throw error;
  } finally {
    console.groupEnd();
  }
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
