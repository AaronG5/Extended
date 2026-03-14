import React, { useState, useEffect } from 'react';
import PowerExtenderSVG from '../components/PowerExtenderSVG';
import DeviceCard from '../components/DeviceCard';
import { fetchAllExtenders, fetchOutletReadings } from '../data/api';

// Adapter: DeviceCard calls fetchHistory(device.id, granularity)
// device.id is "${espId}-${outletIndex}", granularity is Lithuanian period string
function makeHistoryFetcher() {
  return (deviceId, granularity) => {
    const dashIdx = deviceId.lastIndexOf('-');
    const espId      = deviceId.slice(0, dashIdx);
    const outletIndex = Number(deviceId.slice(dashIdx + 1));
    return fetchOutletReadings(espId, outletIndex, granularity);
  };
}

const fetchHistory = makeHistoryFetcher();

function ExtenderSection({ espId, devices }) {
  const slots = [1, 2, 3, 4].map(slotNum => {
    const device = devices.find(d => d.slot === slotNum);
    return {
      slotNumber: slotNum,
      state: device?.pluggedIn ? (device.hasAlert ? 'alert' : 'active') : 'empty',
      deviceName: device?.pluggedIn ? device.name : null,
    };
  });

  const connected    = devices.filter(d => d.pluggedIn).length;
  const disconnected = devices.filter(d => !d.pluggedIn).length;

  return (
    <section className="mb-12">
      <div className="flex items-baseline gap-3 mb-1">
        <h2 className="text-extended-black text-xl font-semibold">Prailgintuvas</h2>
        <span className="text-xs font-mono text-gray-400">{espId}</span>
      </div>
      <p className="text-gray-400 text-sm mb-4">
        {connected} įjungti · {disconnected} išjungti
      </p>

      <PowerExtenderSVG slots={slots} />

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mt-8">
        {devices.map(device => (
          <DeviceCard
            key={device.id}
            device={device}
            fetchHistory={fetchHistory}
          />
        ))}
      </div>
    </section>
  );
}

function DevicesPage() {
  const [extenders, setExtenders] = useState([]);
  const [loading,   setLoading]   = useState(true);
  const [error,     setError]     = useState(null);

  useEffect(() => {
    fetchAllExtenders()
      .then(data => { setExtenders(data); setLoading(false); })
      .catch(err  => { setError(err.message); setLoading(false); });
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64 text-gray-400">
        Kraunama…
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex flex-col items-center justify-center h-64 gap-2">
        <span className="text-red-500 font-medium">Nepavyko gauti duomenų</span>
        <span className="text-gray-400 text-sm">{error}</span>
      </div>
    );
  }

  return (
    <div className="max-w-5xl mx-auto px-4 py-8">
      {extenders.map(({ espId, devices }) => (
        <ExtenderSection key={espId} espId={espId} devices={devices} />
      ))}
    </div>
  );
}

export default DevicesPage;
