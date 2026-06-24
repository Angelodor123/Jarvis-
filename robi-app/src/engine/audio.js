// Web Audio chimes using a single shared AudioContext.
// Do NOT create a new AudioContext per tap — reuse _ctx.
// Do NOT run continuous ambient loops — they interfere with TTS on Android.

let _ctx = null;

function ctx() {
  if (!_ctx && typeof window !== 'undefined' && window.AudioContext) {
    _ctx = new AudioContext();
  }
  return _ctx;
}

function resumeCtx() {
  const c = ctx();
  if (c?.state === 'suspended') c.resume();
  return c;
}

function playTone(frequency, duration, gain = 0.12, type = 'sine') {
  const c = resumeCtx();
  if (!c) return;

  const osc = c.createOscillator();
  const gainNode = c.createGain();

  osc.connect(gainNode);
  gainNode.connect(c.destination);

  osc.type = type;
  osc.frequency.setValueAtTime(frequency, c.currentTime);
  gainNode.gain.setValueAtTime(gain, c.currentTime);
  gainNode.gain.exponentialRampToValueAtTime(0.001, c.currentTime + duration);

  osc.start(c.currentTime);
  osc.stop(c.currentTime + duration);
}

function playSequence(notes, interval = 0.15) {
  const c = resumeCtx();
  if (!c) return;

  notes.forEach(([freq, gain = 0.12], i) => {
    const t = c.currentTime + i * interval;
    const osc = c.createOscillator();
    const gainNode = c.createGain();
    osc.connect(gainNode);
    gainNode.connect(c.destination);
    osc.type = 'sine';
    osc.frequency.setValueAtTime(freq, t);
    gainNode.gain.setValueAtTime(gain, t);
    gainNode.gain.exponentialRampToValueAtTime(0.001, t + 0.12);
    osc.start(t);
    osc.stop(t + 0.15);
  });
}

export const sfx = {
  tap:     () => playTone(720, 0.09, 0.06),
  correct: () => playSequence([[523], [659], [784]]),   // C5 E5 G5
  wrong:   () => playTone(330, 0.25, 0.1),              // E4
  levelUp: () => playSequence([[523], [587], [659], [698], [784]], 0.12),
};
