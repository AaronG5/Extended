import React, { useState, useEffect } from 'react';
import PowerExtenderSVG from '../components/PowerExtenderSVG';
import DeviceCard from '../components/DeviceCard';
import { fetchDevices, fetchPowerHistory } from '../data/testData';

function DevicesPage() {
  const [devices, setDevices] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchDevices().then(data => {
      setDevices(data);
      setLoading(false);
    });
  }, []);

  const slots = [1, 2, 3, 4].map(slotNum => {
    const device = devices.find(d => d.slot === slotNum && d.pluggedIn);
    return {
      slotNumber: slotNum,
      state: device ? (device.hasAlert ? 'alert' : 'active') : 'empty',
      deviceName: device?.name ?? null,
    };
  });

  const sortedDevices = [...devices].sort((a, b) => b.pluggedIn - a.pluggedIn);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64 text-gray-400">
        Loading…
      </div>
    );
  }

  return (
    <div className="max-w-5xl mx-auto px-4 py-8">
      {/* Power extender visual */}
      <section className="mb-10">
        <h2 className="text-extended-black text-xl font-semibold mb-2">Power Extender</h2>
        <p className="text-gray-400 text-sm mb-4">4-socket smart strip — live slot status</p>
        <PowerExtenderSVG slots={slots} />
      </section>

      {/* Device cards */}
      <section>
        <h2 className="text-extended-black text-xl font-semibold mb-1">Devices</h2>
        <p className="text-gray-400 text-sm mb-6">
          {devices.filter(d => d.pluggedIn).length} connected · {devices.filter(d => !d.pluggedIn).length} historical
        </p>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {sortedDevices.map(device => (
            <DeviceCard
              key={device.id}
              device={device}
              fetchHistory={fetchPowerHistory}
            />
          ))}
        </div>
      </section>
    </div>
  );
}

export default DevicesPage;
