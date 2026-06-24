// SVG path data for Robi's 4 mood states.
// Each mood provides: eyes (path d), mouth (path d), extras (array of JSX-compatible shape defs).

export const MOODS = {
  idle: {
    leftEye:  'M -8 -4 Q -8 -8 -4 -8 Q 0 -8 0 -4 Q 0 0 -4 0 Q -8 0 -8 -4',
    rightEye: 'M 4 -4 Q 4 -8 8 -8 Q 12 -8 12 -4 Q 12 0 8 0 Q 4 0 4 -4',
    mouth:    'M -6 8 Q 0 14 6 8',
    extras:   [],
  },
  happy: {
    leftEye:  'M -9 -6 Q -4 -10 1 -6',
    rightEye: 'M 3 -6 Q 8 -10 13 -6',
    mouth:    'M -8 6 Q 0 16 8 6',
    extras:   [],
  },
  thinking: {
    leftEye:  'M -8 -4 Q -8 -8 -4 -8 Q 0 -8 0 -4 Q 0 0 -4 0 Q -8 0 -8 -4',
    rightEye: 'M 4 -4 Q 4 -8 8 -8 Q 12 -8 12 -4 Q 12 0 8 0 Q 4 0 4 -4',
    mouth:    'M -4 10 Q 0 8 4 10',
    // Spinning ring — rendered as a circle with strokeDasharray in the component
    extras: [{ type: 'spinRing' }],
  },
  oops: {
    // X eyes
    leftEye:  'M -9 -8 L -1 0 M -1 -8 L -9 0',
    rightEye: 'M 3 -8 L 11 0 M 11 -8 L 3 0',
    mouth:    'M -6 12 Q 0 8 6 12',
    extras:   [],
  },
};
