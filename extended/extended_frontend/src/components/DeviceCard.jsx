import { useState, useEffect } from 'react';
import {
  LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer,
} from 'recharts';

const PERIODS      = ['diena', 'savaitė', 'mėnesis'];
const GRANULARITIES = ['valanda', 'diena', 'savaitė'];

function PeriodToggle({ value, options, onChange }) {
  return (
    <div className="flex gap-1">
      {options.map(opt => (
        <button
          key={opt}
          onClick={() => onChange(opt)}
          className={`text-xs px-2 py-0.5 rounded-full capitalize transition-colors ${
            value === opt
              ? 'bg-extended-black text-white'
              : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
          }`}
        >
          {opt}
        </button>
      ))}
    </div>
  );
}

function ShieldOkIcon() {
  return (
    <svg viewBox="0 0 24 24" className="w-8 h-8" fill="none" xmlns="http://www.w3.org/2000/svg">
      <path d="M12 3L4 6.5V12c0 4 3.5 7.4 8 8.5 4.5-1.1 8-4.5 8-8.5V6.5L12 3z" fill="#dcfce7" stroke="#16a34a" strokeWidth="1.6" strokeLinejoin="round" />
      <path d="M9 12l2 2 4-4" stroke="#16a34a" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

function WarnIcon() {
  return (
    <svg viewBox="0 0 24 24" className="w-8 h-8" fill="none" xmlns="http://www.w3.org/2000/svg">
      <path d="M12 3L2 21h20L12 3z" fill="#fef9c3" stroke="#ca8a04" strokeWidth="1.8" strokeLinejoin="round" />
      <path d="M12 10v4" stroke="#ca8a04" strokeWidth="2" strokeLinecap="round" />
      <circle cx="12" cy="17.5" r="1" fill="#ca8a04" />
    </svg>
  );
}

function DeviceCard({ device, fetchHistory }) {
  const [isFlipped, setIsFlipped]       = useState(false);
  const [kwhPeriod, setKwhPeriod]       = useState('day');
  const [granularity, setGranularity]   = useState('day');
  const [historyData, setHistoryData]   = useState([]);
  const [loadingGraph, setLoadingGraph] = useState(false);

  // Name editing
  // TODO: replace confirmName / saveName with API calls
  const [deviceName, setDeviceName]     = useState(device.name);
  const [isEditing, setIsEditing]       = useState(false);
  const [editValue, setEditValue]       = useState(device.name);

  // Use measured kWh from API when available, otherwise estimate from wattage
  const kwh = device.kwhRecorded != null
    ? device.kwhRecorded.toFixed(4)
    : ((device.currentPowerDraw * (kwhPeriod === 'day' ? 24 : kwhPeriod === 'week' ? 168 : 720)) / 1000).toFixed(2);
  const kwhLabel = device.kwhRecorded != null ? 'kWh total' : 'kWh';

  function handleConfirm() {
    const trimmed = editValue.trim() || deviceName;
    setDeviceName(trimmed);
    setEditValue(trimmed);
    setIsEditing(false);
    // TODO: PATCH /devices/:id { name: trimmed }
  }

  function handleEdit() {
    setEditValue(deviceName);
    setIsEditing(true);
  }

  function handleKeyDown(e) {
    if (e.key === 'Enter') handleConfirm();
    if (e.key === 'Escape') { setIsEditing(false); setEditValue(deviceName); }
  }

  useEffect(() => {
    if (!isFlipped) return;
    setLoadingGraph(true);
    fetchHistory(device.id, granularity).then(data => {
      setHistoryData(data);
      setLoadingGraph(false);
    });
  }, [isFlipped, granularity, device.id, fetchHistory]);

  const active = device.buttonState;

  return (
    <div style={{ perspective: '1000px' }} className="w-full h-72">
      <div
        style={{
          transformStyle: 'preserve-3d',
          transition: 'transform 0.55s cubic-bezier(0.4, 0.2, 0.2, 1)',
          transform: isFlipped ? 'rotateY(180deg)' : 'rotateY(0deg)',
          position: 'relative',
          width: '100%',
          height: '100%',
        }}
      >
        {/* ── FRONT ── */}
        <div
          style={{ backfaceVisibility: 'hidden', WebkitBackfaceVisibility: 'hidden' }}
          className={`absolute inset-0 rounded-2xl p-5 flex flex-col shadow-md border-2 bg-white ${
            active ? 'border-extended-black' : 'border-gray-200 opacity-75'
          }`}
        >
          {/* Connected indicator */}
          <div className="flex items-center gap-2 mb-3">
            <span className={`inline-block w-2.5 h-2.5 rounded-full ${active ? 'bg-green-400' : 'bg-gray-300'}`} />
            <span className="text-xs text-gray-400">{active ? 'Connected' : 'Disconnected'}</span>
          </div>

          {/* Device name — editable. Button is absolute so it never shifts the text's center. */}
          <div className="relative flex items-center justify-center mb-3">
            {isEditing ? (
              <input
                autoFocus
                value={editValue}
                onChange={e => setEditValue(e.target.value)}
                onKeyDown={handleKeyDown}
                className="text-lg font-semibold text-extended-black text-center border-b-2 border-extended-black bg-transparent outline-none w-36"
              />
            ) : (
              <h3 className="text-lg font-semibold text-extended-black">
                {deviceName}
              </h3>
            )}

            {/* Pencil → Checkmark toggle — absolute so it doesn't affect text centering */}
            {isEditing ? (
              <button
                onClick={handleConfirm}
                title="Confirm name"
                className="absolute right-0 w-6 h-6 rounded-full bg-green-100 text-green-600 hover:bg-green-200 flex items-center justify-center transition-colors"
              >
                <svg viewBox="0 0 16 16" className="w-3.5 h-3.5" fill="none">
                  <path d="M3 8.5l3 3 7-7" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
                </svg>
              </button>
            ) : (
              <button
                onClick={handleEdit}
                title="Edit name"
                className="absolute right-0 w-6 h-6 rounded-full bg-gray-100 text-gray-400 hover:bg-blue-100 hover:text-extended-black flex items-center justify-center transition-colors"
              >
                <svg viewBox="0 0 16 16" className="w-3.5 h-3.5" fill="none">
                  <path d="M11 2l3 3-8 8H3v-3l8-8z" stroke="currentColor" strokeWidth="1.5" strokeLinejoin="round" />
                </svg>
              </button>
            )}
          </div>

          {/*
            3-col × 2-row grid.
            Row 1 (1fr)   — values/icons, all vertically centered together.
            Row 2 (auto)  — only col 2 has the period toggle; cols 1 & 3 are empty.
          */}
          <div
            style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gridTemplateRows: '1fr auto', flex: 1 }}
          >
            {/* Row 1, Col 1 — watts */}
            <div className="flex flex-col items-center justify-center">
              <span className="text-2xl font-bold text-extended-black leading-none">
                {active ? Number(device.currentPowerDraw).toFixed(1) : '—'}
              </span>
              <span className="text-xs text-gray-400 mt-1">Watts</span>
            </div>

            {/* Row 1, Col 2 — kWh */}
            <div className="flex flex-col items-center justify-center">
              <span className="text-2xl font-bold text-extended-black leading-none">
                {active ? kwh : '—'}
              </span>
              <span className="text-xs text-gray-400 mt-1">{kwhLabel}</span>
            </div>

            {/* Row 1, Col 3 — status */}
            <div className="flex flex-col items-center justify-center gap-1">
              {device.hasAlert ? <WarnIcon /> : <ShieldOkIcon />}
              <span className={`text-xs text-center leading-tight ${device.hasAlert ? 'text-yellow-600' : 'text-green-600'}`}>
                {device.hasAlert ? device.alertMessage : 'OK'}
              </span>
            </div>

            {/* Row 2, Col 1 — empty */}
            <div />

            {/* Row 2, Col 2 — period toggle */}
            <div className="flex justify-center items-center py-1">
              <PeriodToggle value={kwhPeriod} options={PERIODS} onChange={setKwhPeriod} />
            </div>

            {/* Row 2, Col 3 — empty */}
            <div />
          </div>

          {/* Graph button */}
          <div className="flex justify-center mt-3">
            <button
              onClick={() => setIsFlipped(true)}
              className="bg-extended-black text-white text-sm px-6 py-1.5 rounded-full hover:opacity-80 transition-opacity"
            >
              Grafikas ▶
            </button>
          </div>
        </div>

        {/* ── BACK ── */}
        <div
          style={{
            backfaceVisibility: 'hidden',
            WebkitBackfaceVisibility: 'hidden',
            transform: 'rotateY(180deg)',
          }}
          className={`absolute inset-0 rounded-2xl p-5 flex flex-col shadow-md border-2 bg-white ${
            active ? 'border-extended-black' : 'border-gray-200 opacity-75'
          }`}
        >
          <div className="flex items-center justify-between mb-2">
            <button
              onClick={() => setIsFlipped(false)}
              className="text-extended-black text-sm font-medium hover:opacity-70"
            >
              ← Atgal
            </button>
            <span className="text-sm font-semibold text-extended-black">{deviceName}</span>
            <PeriodToggle value={granularity} options={GRANULARITIES} onChange={setGranularity} />
          </div>

          <div className="flex-1">
            {loadingGraph ? (
              <div className="flex items-center justify-center h-full text-gray-400 text-sm">Loading…</div>
            ) : historyData.length === 0 ? (
              <div className="flex items-center justify-center h-full text-gray-400 text-sm">No data</div>
            ) : (
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={historyData} margin={{ top: 4, right: 8, left: 0, bottom: 0 }}>
                  <XAxis dataKey="time" tick={{ fontSize: 9, fill: '#6b7280' }} interval="preserveStartEnd" tickLine={false} />
                  <YAxis tick={{ fontSize: 9, fill: '#6b7280' }} width={36} tickLine={false} axisLine={false} tickFormatter={v => `${v}W`} />
                  <Tooltip formatter={v => [`${v} W`, 'Power']} contentStyle={{ fontSize: 11, borderRadius: 8 }} />
                  <Line type="monotone" dataKey="watts" stroke="#172e62" strokeWidth={2} dot={false} activeDot={{ r: 4 }} />
                </LineChart>
              </ResponsiveContainer>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

export default DeviceCard;
