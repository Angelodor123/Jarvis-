// TTS abstraction with Android WebView fixes.
// Key rules:
//   1. Always cancel() then wait 50ms before speaking — fixes Android stuck state.
//   2. Never call speak() inside a Promise.then() or after await — must be sync.
//   3. Prefer Google/Natural/Enhanced voices when available.

let _voices = [];
let _voicesLoaded = false;

function loadVoices() {
  _voices = window.speechSynthesis?.getVoices() ?? [];
  _voicesLoaded = _voices.length > 0;
}

if (typeof window !== 'undefined') {
  loadVoices();
  window.speechSynthesis?.addEventListener('voiceschanged', loadVoices);
}

function pickVoice(lang = 'en-US') {
  if (!_voicesLoaded) loadVoices();

  const priority = ['Google', 'Natural', 'Enhanced'];
  const langCode = lang.toLowerCase();

  // Filter to matching language
  const matches = _voices.filter(v => v.lang.toLowerCase().startsWith(langCode.slice(0, 2)));

  // Prefer high-quality voices
  for (const keyword of priority) {
    const hit = matches.find(v => v.name.includes(keyword));
    if (hit) return hit;
  }

  return matches[0] ?? null;
}

/**
 * Speak text aloud. Call synchronously within a user gesture.
 * @param {string} text
 * @param {string} lang - BCP-47 language tag, e.g. 'en-US' or 'he-IL'
 * @param {number} rate - speech rate (0.8 default, slower for kids)
 */
export function speak(text, lang = 'en-US', rate = 0.85) {
  if (typeof window === 'undefined' || !window.speechSynthesis) return;

  const synth = window.speechSynthesis;

  // Android fix: cancel existing speech then sync-speak after minimal delay
  synth.cancel();

  const utter = new SpeechSynthesisUtterance(text);
  utter.lang = lang;
  utter.rate = rate;
  utter.pitch = 1.1;

  const voice = pickVoice(lang);
  if (voice) utter.voice = voice;

  // 50ms delay required on Android to avoid stuck speech queue
  setTimeout(() => synth.speak(utter), 50);
}

/**
 * Stop any current speech.
 */
export function stopSpeech() {
  window.speechSynthesis?.cancel();
}

/**
 * Returns true if TTS appears to be available (best-effort).
 * TTS is blocked inside Claude artifact iframes.
 */
export function isSpeechAvailable() {
  return typeof window !== 'undefined' && 'speechSynthesis' in window;
}
