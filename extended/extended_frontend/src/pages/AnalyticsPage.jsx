import React, { useState, useEffect } from 'react';
import {
  PieChart, Pie, Cell, Tooltip as PieTooltip,
  LineChart, Line, XAxis, YAxis, Tooltip as LineTooltip, ResponsiveContainer,
} from 'recharts';
import {
  fetchDeviceKwh, fetchEnergyPrices, fetchStandbyPower, fetchAlerts,
} from '../data/testData';

const PIE_COLORS = ['#172e62', '#2563eb', '#3b82f6', '#60a5fa', '#93c5fd', '#bfdbfe', '#e0f2fe'];
const PERIODS = ['day', 'week', 'month'];
const OTHER_THRESHOLD = 0.01; // group slices below 1%

/** Collapse slices that represent < 1% of the total into a single "Other" slice */
function groupSmallSlices(data) {
  const total = data.reduce((s, d) => s + d.kwh, 0);
  if (total === 0) return data;
  const big   = data.filter(d => d.kwh / total >= OTHER_THRESHOLD);
  const small = data.filter(d => d.kwh / total <  OTHER_THRESHOLD);
  if (small.length === 0) return big;
  const otherKwh = small.reduce((s, d) => s + d.kwh, 0);
  return [...big, { id: -1, name: 'Other', kwh: parseFloat(otherKwh.toFixed(2)) }];
}

function CheckIcon() {
  return (
    <svg viewBox="0 0 24 24" className="w-5 h-5" fill="none" xmlns="http://www.w3.org/2000/svg">
      <circle cx="12" cy="12" r="11" fill="#dcfce7" />
      <path d="M7 12.5l3.5 3.5 6.5-7" stroke="#16a34a" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

function WarnIcon({ color = '#ca8a04' }) {
  return (
    <svg viewBox="0 0 24 24" className="w-5 h-5 shrink-0" fill="none" xmlns="http://www.w3.org/2000/svg">
      <path d="M12 3L2 21h20L12 3z" fill="#fef9c3" stroke={color} strokeWidth="1.8" strokeLinejoin="round" />
      <path d="M12 10v4" stroke={color} strokeWidth="2" strokeLinecap="round" />
      <circle cx="12" cy="17.5" r="1" fill={color} />
    </svg>
  );
}

function Card({ title, children }) {
  return (
    <div className="bg-white rounded-2xl border-2 border-gray-100 shadow-md p-6">
      <h3 className="text-extended-black font-semibold text-lg mb-4">{title}</h3>
      {children}
    </div>
  );
}

function PeriodToggle({ value, onChange }) {
  return (
    <div className="flex gap-1 mb-4">
      {PERIODS.map(p => (
        <button
          key={p}
          onClick={() => onChange(p)}
          className={`text-xs px-3 py-1 rounded-full capitalize transition-colors ${
            value === p ? 'bg-extended-black text-white' : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
          }`}
        >
          {p}
        </button>
      ))}
    </div>
  );
}

function AnalyticsPage() {
  const [kwhPeriod, setKwhPeriod] = useState('day');
  const [kwhData,   setKwhData]   = useState([]);
  const [prices,    setPrices]    = useState([]);
  const [standby,   setStandby]   = useState(0);
  const [alerts,    setAlerts]    = useState([]);
  const [loading,   setLoading]   = useState(true);

  useEffect(() => {
    Promise.all([fetchEnergyPrices(), fetchStandbyPower(), fetchAlerts()]).then(
      ([p, s, a]) => { setPrices(p); setStandby(s); setAlerts(a); setLoading(false); }
    );
  }, []);

  useEffect(() => {
    fetchDeviceKwh(kwhPeriod).then(raw => setKwhData(groupSmallSlices(raw)));
  }, [kwhPeriod]);

  if (loading) {
    return <div className="flex items-center justify-center h-64 text-gray-400">Loading…</div>;
  }

  const standbyKwhDay   = (standby * 24 / 1000).toFixed(3);
  const standbyKwhMonth = (standby * 24 * 30 / 1000).toFixed(1);

  return (
    <div className="max-w-5xl mx-auto px-4 py-8">
      <h2 className="text-extended-black text-xl font-semibold mb-1">Analytics</h2>
      <p className="text-gray-400 text-sm mb-6">Energy overview and system insights</p>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">

        {/* Card 1 — Energy by device (pie) */}
        <Card title="Energy by Device">
          <PeriodToggle value={kwhPeriod} onChange={setKwhPeriod} />
          <ResponsiveContainer width="100%" height={220}>
            <PieChart>
              <Pie
                data={kwhData}
                dataKey="kwh"
                nameKey="name"
                cx="50%"
                cy="50%"
                outerRadius={80}
                label={({ name, percent }) => percent > 0.03 ? `${name} ${(percent * 100).toFixed(0)}%` : ''}
                labelLine={false}
              >
                {kwhData.map((_, i) => (
                  <Cell key={i} fill={PIE_COLORS[i % PIE_COLORS.length]} />
                ))}
              </Pie>
              <PieTooltip formatter={v => [`${v} kWh`]} />
            </PieChart>
          </ResponsiveContainer>
        </Card>

        {/* Card 2 — Energy price */}
        <Card title="Energy Price">
          <p className="text-xs text-gray-400 mb-3">€/kWh over last 24 hours</p>
          <ResponsiveContainer width="100%" height={220}>
            <LineChart data={prices} margin={{ top: 4, right: 8, left: 0, bottom: 0 }}>
              <XAxis dataKey="time" tick={{ fontSize: 9, fill: '#6b7280' }} interval={7} tickLine={false} />
              <YAxis tick={{ fontSize: 9, fill: '#6b7280' }} width={46} tickLine={false} axisLine={false} tickFormatter={v => `€${v.toFixed(2)}`} />
              <LineTooltip formatter={v => [`€${Number(v).toFixed(4)}/kWh`, 'Price']} contentStyle={{ fontSize: 11, borderRadius: 8 }} />
              <Line type="monotone" dataKey="price" stroke="#172e62" strokeWidth={2} dot={false} activeDot={{ r: 4 }} />
            </LineChart>
          </ResponsiveContainer>
        </Card>

        {/* Card 3 — Standby */}
        <Card title="Standby Consumption">
          <div className="flex flex-col items-center justify-center h-40 gap-2">
            <span className="text-5xl font-bold text-extended-black">{standby}</span>
            <span className="text-gray-500 text-sm">Watts idle</span>
            <div className="flex gap-6 mt-2 text-center">
              <div>
                <p className="text-lg font-semibold text-extended-black">{standbyKwhDay}</p>
                <p className="text-xs text-gray-400">kWh / day</p>
              </div>
              <div>
                <p className="text-lg font-semibold text-extended-black">{standbyKwhMonth}</p>
                <p className="text-xs text-gray-400">kWh / month</p>
              </div>
            </div>
          </div>
        </Card>

        {/* Card 4 — Alerts */}
        <Card title="Alerts">
          {alerts.length === 0 ? (
            <div className="flex items-center gap-2 text-green-600 text-sm">
              <CheckIcon />
              <span>No active alerts</span>
            </div>
          ) : (
            <ul className="space-y-3 overflow-y-auto max-h-52">
              {alerts.map(alert => (
                <li
                  key={alert.id}
                  className="flex items-start gap-3 p-3 rounded-xl bg-yellow-50 border border-yellow-200"
                >
                  <WarnIcon />
                  <div>
                    <p className="text-sm font-medium text-gray-800">{alert.message}</p>
                    <p className="text-xs text-gray-400 mt-0.5">
                      {new Date(alert.timestamp).toLocaleString()}
                    </p>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </Card>

      </div>
    </div>
  );
}

export default AnalyticsPage;
