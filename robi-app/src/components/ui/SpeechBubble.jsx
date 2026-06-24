import React from 'react';

export default function SpeechBubble({ text, style = {} }) {
  if (!text) return null;

  return (
    <div style={{
      position: 'relative',
      background: 'white',
      borderRadius: 16,
      padding: '12px 18px',
      boxShadow: '0 4px 16px rgba(91,75,138,0.15)',
      fontFamily: "'Nunito', system-ui",
      fontSize: 16,
      color: '#3a2f5b',
      lineHeight: 1.5,
      maxWidth: 280,
      ...style,
    }}>
      {/* Tail pointing left toward Robi */}
      <div style={{
        position: 'absolute',
        left: -10,
        top: 18,
        width: 0,
        height: 0,
        borderTop: '8px solid transparent',
        borderBottom: '8px solid transparent',
        borderRight: '12px solid white',
      }} />
      {text}
    </div>
  );
}
