import React from 'react';
import { NavLink } from 'react-router-dom';

const NAV_ITEMS = [
  { label: 'Įrenginiai',   to: '/devices'   },
  { label: 'Suvestinė', to: '/analytics' },
  { label: 'Profilis',   to: '/profile'   },
];

function Navigation() {
  return (
    <nav className="h-20 w-full bg-extended-white border-gray-200 border-b-2 text-extended-black flex items-center justify-between sticky top-0 z-50 shadow-sm">
      {/* Brand */}
      <div className="pl-6">
        <span className="font-bold text-lg tracking-tight text-extended-black">Extended</span>
      </div>

      {/* Nav links */}
      <ul className="flex gap-1">
        {NAV_ITEMS.map(({ label, to }) => (
          <li key={to}>
            <NavLink
              to={to}
              className={({ isActive }) =>
                `px-5 py-2 rounded-lg text-base font-medium transition-colors ${
                  isActive
                    ? 'bg-extended-black text-white'
                    : 'text-extended-black hover:bg-gray-100'
                }`
              }
            >
              {label}
            </NavLink>
          </li>
        ))}
      </ul>

      {/* right-side spacer to keep links centred */}
      <div className="w-24" />
    </nav>
  );
}

export default Navigation;
