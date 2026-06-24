import React, { useEffect, useRef } from 'react';
import ForestTree from './ForestTree.jsx';

// Full parallax forest background. Children are rendered on top.
// scrollY: passed from ForestPath to drive parallax.

export default function ParallaxForest({ scrollY = 0, children }) {
  return (
    <div style={{
      position: 'fixed',
      inset: 0,
      overflow: 'hidden',
      background: 'linear-gradient(180deg, #FFD5A8 0%, #FFF0D4 30%, #E8F5E0 70%, #C8E6C0 100%)',
    }}>
      {/* Sky layer — slowest parallax */}
      <div style={{ transform: `translateY(${scrollY * 0.08}px)`, willChange: 'transform' }}>
        {/* Glowing sun */}
        <div style={{
          position: 'absolute',
          top: 30,
          right: 60,
          width: 80,
          height: 80,
          borderRadius: '50%',
          background: 'radial-gradient(circle, #FFE066 40%, #FFB648 100%)',
          boxShadow: '0 0 40px 20px rgba(255,180,0,0.3)',
        }} />
        {/* Mountain silhouettes */}
        <svg style={{ position: 'absolute', bottom: '40%', left: 0, width: '100%' }} viewBox="0 0 400 120" preserveAspectRatio="none">
          <path d="M0 120 L60 40 L120 80 L200 20 L280 70 L340 30 L400 60 L400 120Z" fill="#C8B8E8" opacity="0.4" />
          <path d="M0 120 L80 60 L160 90 L240 50 L320 80 L400 50 L400 120Z" fill="#B8A8D8" opacity="0.3" />
        </svg>
        {/* Clouds */}
        <Cloud x="10%" y={60} delay={0} />
        <Cloud x="55%" y={40} delay={3} />
        <Cloud x="75%" y={70} delay={6} />
        {/* Firefly dots */}
        {[...Array(8)].map((_, i) => (
          <div key={i} style={{
            position: 'absolute',
            left: `${10 + i * 11}%`,
            top: `${15 + (i % 3) * 12}%`,
            width: 5,
            height: 5,
            borderRadius: '50%',
            background: '#FFD976',
            opacity: 0.6,
            animation: `fireflyDrift ${3 + i * 0.7}s ease-in-out infinite`,
            animationDelay: `${i * 0.4}s`,
          }} />
        ))}
      </div>

      {/* Tree layer — medium parallax */}
      <div style={{ transform: `translateY(${scrollY * 0.35}px)`, willChange: 'transform', position: 'absolute', bottom: 0, width: '100%' }}>
        <svg viewBox="0 0 400 200" preserveAspectRatio="none" style={{ position: 'absolute', bottom: 0, width: '100%', height: 200 }}>
          {/* Ground moss */}
          <ellipse cx="200" cy="195" rx="220" ry="12" fill="#8BC34A" opacity="0.5" />
          {/* Trees */}
          <ForestTree x={20}  h={140} color="#4CAF50" />
          <ForestTree x={60}  h={110} color="#66BB6A" />
          <ForestTree x={310} h={130} color="#388E3C" />
          <ForestTree x={350} h={100} color="#4CAF50" />
          {/* Mushrooms */}
          <g transform="translate(90, 175)">
            <rect x="-4" y="-16" width="8" height="16" fill="#DEB887" rx="2" />
            <ellipse cx="0" cy="-16" rx="12" ry="8" fill="#F44336" />
            <circle cx="-4" cy="-18" r="2" fill="white" opacity="0.8" />
            <circle cx="3"  cy="-20" r="1.5" fill="white" opacity="0.8" />
          </g>
          <g transform="translate(270, 180)">
            <rect x="-3" y="-12" width="6" height="12" fill="#DEB887" rx="2" />
            <ellipse cx="0" cy="-12" rx="9" ry="6" fill="#9C27B0" />
          </g>
          {/* Flowers */}
          {[100, 150, 230, 290].map((x, i) => (
            <g key={i} transform={`translate(${x}, 185)`}>
              <circle cx="0" cy="-8" r="5" fill={['#FF9FBE','#FFD976','#FF6B5B','#80DEEA'][i]} opacity="0.9" />
              <rect x="-1.5" y="-3" width="3" height="10" fill="#66BB6A" rx="1" />
            </g>
          ))}
        </svg>
      </div>

      {/* Content on top */}
      <div style={{ position: 'relative', zIndex: 1, height: '100%' }}>
        {children}
      </div>
    </div>
  );
}

function Cloud({ x, y, delay }) {
  return (
    <div style={{
      position: 'absolute',
      left: x,
      top: y,
      animation: `cloudDrift ${18 + delay}s ease-in-out infinite alternate`,
      animationDelay: `${delay}s`,
    }}>
      <svg width="90" height="40" viewBox="0 0 90 40">
        <ellipse cx="45" cy="30" rx="40" ry="16" fill="white" opacity="0.85" />
        <ellipse cx="30" cy="24" rx="22" ry="18" fill="white" opacity="0.85" />
        <ellipse cx="58" cy="22" rx="20" ry="16" fill="white" opacity="0.8" />
      </svg>
    </div>
  );
}
