import React from 'react';

// Single illustrated SVG tree for the forest layer.
// x: horizontal position, h: height, color: canopy color

export default function ForestTree({ x = 0, h = 120, color = '#4CAF50' }) {
  const trunkH = h * 0.35;
  const trunkW = h * 0.08;
  const c1r = h * 0.28;
  const c2r = h * 0.23;
  const c3r = h * 0.18;

  return (
    <g transform={`translate(${x}, ${200 - trunkH})`}>
      {/* Trunk */}
      <rect
        x={-trunkW / 2}
        y={0}
        width={trunkW}
        height={trunkH}
        rx={trunkW * 0.4}
        fill="#795548"
      />
      {/* Canopy layers (bottom to top for depth) */}
      <ellipse cx="0" cy={-h * 0.45} rx={c1r} ry={c1r * 0.75} fill={color} opacity="0.7" />
      <ellipse cx="0" cy={-h * 0.6}  rx={c2r} ry={c2r * 0.75} fill={color} opacity="0.85" />
      <ellipse cx="0" cy={-h * 0.72} rx={c3r} ry={c3r * 0.75} fill={color} />
    </g>
  );
}
