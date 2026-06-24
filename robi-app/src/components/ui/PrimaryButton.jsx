import React from 'react';
import { sfx } from '../../engine/audio.js';

export default function PrimaryButton({ children, onClick, color = '#FF6B5B', disabled = false, style = {} }) {
  function handleClick(e) {
    if (disabled) return;
    sfx.tap();
    onClick?.(e);
  }

  return (
    <button
      onClick={handleClick}
      disabled={disabled}
      style={{
        background: disabled ? '#ccc' : `linear-gradient(135deg, ${color}, ${color}cc)`,
        color: 'white',
        border: 'none',
        borderRadius: 20,
        padding: '14px 28px',
        fontSize: 18,
        fontFamily: "'Baloo 2', 'Varela Round', system-ui",
        fontWeight: 700,
        cursor: disabled ? 'default' : 'pointer',
        boxShadow: disabled ? 'none' : `0 4px 0 ${color}99, 0 6px 12px ${color}44`,
        transform: 'translateY(0)',
        transition: 'transform 0.1s, box-shadow 0.1s',
        userSelect: 'none',
        WebkitTapHighlightColor: 'transparent',
        ...style,
      }}
      onPointerDown={e => {
        if (!disabled) e.currentTarget.style.transform = 'translateY(2px)';
      }}
      onPointerUp={e => {
        e.currentTarget.style.transform = 'translateY(0)';
      }}
    >
      {children}
    </button>
  );
}
