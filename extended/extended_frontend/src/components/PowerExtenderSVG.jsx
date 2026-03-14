
const SLOT_COLORS = {
  active: '#22c55e',
  alert:  '#eab308',
  empty:  '#9ca3af',
};

const SLOT_CX = [75, 185, 295, 405];
// Body spans y=30..100 → center at y=65
const CY = 65;
const R  = 24;

function PowerExtenderSVG({ slots = [], onSlotClick }) {
  return (
    <div className="flex justify-center py-4">
      <svg
        viewBox="0 0 500 130"
        className="w-full max-w-2xl drop-shadow-md"
        xmlns="http://www.w3.org/2000/svg"
      >
        {/* Power cord — vertically centered on body (y=55 → center=65) */}
        <rect x="0" y="55" width="22" height="20" rx="4" fill="#6b7280" />

        {/* Extender body */}
        <rect x="18" y="30" width="470" height="70" rx="20" fill="#172e62" />

        {/* Inner recess */}
        <rect x="24" y="36" width="458" height="58" rx="16" fill="#1e3a7a" />

        {slots.map((slot, i) => {
          const cx = SLOT_CX[i];
          const color = SLOT_COLORS[slot.state] ?? SLOT_COLORS.empty;
          const isAlert = slot.state === 'alert';

          return (
            <g
              key={slot.slotNumber}
              onClick={() => onSlotClick?.(slot.slotNumber)}
              style={{ cursor: onSlotClick ? 'pointer' : 'default' }}
            >
              {/* Device name above slot */}
              {slot.deviceName && (
                <text
                  x={cx}
                  y="22"
                  textAnchor="middle"
                  fontSize="11"
                  fontWeight="600"
                  fill="#172e62"
                  fontFamily="system-ui, sans-serif"
                >
                  {slot.deviceName}
                </text>
              )}

              {/* Socket circle */}
              <circle cx={cx} cy={CY} r={R} fill={color} />

              {/* Slot number (empty slots) */}
              {slot.state === 'empty' && (
                <text
                  x={cx}
                  y={CY + 1}
                  textAnchor="middle"
                  dominantBaseline="middle"
                  fontSize="10"
                  fill="#fff"
                  opacity="0.6"
                  fontFamily="system-ui, sans-serif"
                >
                  {slot.slotNumber}
                </text>
              )}

              {/* European Type C pin holes — two round holes side by side */}
              {slot.state !== 'empty' && (
                <>
                  <circle cx={cx - 8} cy={CY} r="4" fill="#fff" opacity="0.75" />
                  <circle cx={cx + 8} cy={CY} r="4" fill="#fff" opacity="0.75" />
                </>
              )}

              {/* Alert badge */}
              {isAlert && (
                <>
                  <circle cx={cx + R - 4} cy={CY - R + 4} r="8" fill="#ef4444" />
                  <text
                    x={cx + R - 4}
                    y={CY - R + 4}
                    textAnchor="middle"
                    dominantBaseline="middle"
                    fontSize="10"
                    fontWeight="bold"
                    fill="#fff"
                    fontFamily="system-ui, sans-serif"
                  >
                    !
                  </text>
                </>
              )}
            </g>
          );
        })}
      </svg>
    </div>
  );
}

export default PowerExtenderSVG;
