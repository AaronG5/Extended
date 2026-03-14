import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import Navigation from './components/Navigation';
import DevicesPage from './pages/DevicesPage';
import AnalyticsPage from './pages/AnalyticsPage';
import ProfilePage from './pages/ProfilePage';

function App() {
  return (
    <BrowserRouter>
      <div className="min-h-screen bg-gray-50">
        <Navigation />
        <main>
          <Routes>
            <Route path="/" element={<Navigate to="/devices" replace />} />
            <Route path="/devices"   element={<DevicesPage />}   />
            <Route path="/analytics" element={<AnalyticsPage />} />
            <Route path="/profile"   element={<ProfilePage />}   />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  );
}

export default App;
