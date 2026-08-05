// Lightweight synthesized HUD SFX (Web Audio). No external assets required.
(() => {
  let ctx = null;
  let unlocked = false;

  function ac() {
    if (!ctx) {
      const Ctx = window.AudioContext || window.webkitAudioContext;
      if (!Ctx) return null;
      ctx = new Ctx();
    }
    if (ctx.state === "suspended") ctx.resume();
    unlocked = true;
    return ctx;
  }

  function tone({
    freq = 440,
    freqEnd = null,
    type = "sine",
    duration = 0.12,
    gain = 0.08,
    delay = 0,
    attack = 0.005,
    release = 0.08,
  }) {
    const audio = ac();
    if (!audio) return;
    const t0 = audio.currentTime + delay;
    const osc = audio.createOscillator();
    const g = audio.createGain();
    osc.type = type;
    osc.frequency.setValueAtTime(freq, t0);
    if (freqEnd != null) {
      osc.frequency.exponentialRampToValueAtTime(Math.max(40, freqEnd), t0 + duration);
    }
    g.gain.setValueAtTime(0.0001, t0);
    g.gain.exponentialRampToValueAtTime(gain, t0 + attack);
    g.gain.exponentialRampToValueAtTime(0.0001, t0 + Math.max(attack + 0.02, duration - release));
    osc.connect(g);
    g.connect(audio.destination);
    osc.start(t0);
    osc.stop(t0 + duration + 0.02);
  }

  function noiseBurst({ duration = 0.08, gain = 0.04, delay = 0, band = 2000 }) {
    const audio = ac();
    if (!audio) return;
    const n = Math.floor(audio.sampleRate * duration);
    const buffer = audio.createBuffer(1, n, audio.sampleRate);
    const data = buffer.getChannelData(0);
    for (let i = 0; i < n; i++) data[i] = (Math.random() * 2 - 1) * (1 - i / n);
    const src = audio.createBufferSource();
    src.buffer = buffer;
    const filter = audio.createBiquadFilter();
    filter.type = "bandpass";
    filter.frequency.value = band;
    filter.Q.value = 0.8;
    const g = audio.createGain();
    const t0 = audio.currentTime + delay;
    g.gain.setValueAtTime(gain, t0);
    g.gain.exponentialRampToValueAtTime(0.0001, t0 + duration);
    src.connect(filter);
    filter.connect(g);
    g.connect(audio.destination);
    src.start(t0);
    src.stop(t0 + duration + 0.02);
  }

  const sfx = {
    unlock() {
      ac();
    },
    boot() {
      tone({ freq: 220, freqEnd: 660, type: "triangle", duration: 0.28, gain: 0.07 });
      tone({ freq: 440, freqEnd: 880, type: "sine", duration: 0.35, gain: 0.05, delay: 0.08 });
      noiseBurst({ duration: 0.12, gain: 0.03, delay: 0.02, band: 1800 });
    },
    connected() {
      tone({ freq: 520, type: "sine", duration: 0.08, gain: 0.06 });
      tone({ freq: 780, type: "sine", duration: 0.1, gain: 0.05, delay: 0.07 });
    },
    wake() {
      tone({ freq: 380, freqEnd: 760, type: "sawtooth", duration: 0.16, gain: 0.045 });
      tone({ freq: 760, freqEnd: 1140, type: "sine", duration: 0.18, gain: 0.06, delay: 0.05 });
      noiseBurst({ duration: 0.1, gain: 0.035, delay: 0.02, band: 2400 });
    },
    listen() {
      tone({ freq: 640, type: "sine", duration: 0.06, gain: 0.04 });
    },
    think() {
      tone({ freq: 300, type: "triangle", duration: 0.07, gain: 0.035 });
      tone({ freq: 450, type: "triangle", duration: 0.07, gain: 0.03, delay: 0.08 });
      tone({ freq: 600, type: "triangle", duration: 0.07, gain: 0.025, delay: 0.16 });
    },
    speak() {
      tone({ freq: 280, freqEnd: 420, type: "sine", duration: 0.14, gain: 0.045 });
    },
    timerStart() {
      tone({ freq: 880, type: "square", duration: 0.06, gain: 0.035 });
      tone({ freq: 1175, type: "square", duration: 0.08, gain: 0.03, delay: 0.07 });
      tone({ freq: 1480, type: "sine", duration: 0.12, gain: 0.04, delay: 0.14 });
    },
    timerDone() {
      tone({ freq: 660, type: "sine", duration: 0.1, gain: 0.06 });
      tone({ freq: 880, type: "sine", duration: 0.12, gain: 0.05, delay: 0.1 });
      tone({ freq: 1175, type: "triangle", duration: 0.2, gain: 0.045, delay: 0.2 });
    },
    error() {
      tone({ freq: 240, freqEnd: 120, type: "sawtooth", duration: 0.28, gain: 0.05 });
      noiseBurst({ duration: 0.15, gain: 0.04, band: 900 });
    },
    click() {
      tone({ freq: 1000, type: "square", duration: 0.03, gain: 0.025 });
    },
    offline() {
      tone({ freq: 400, freqEnd: 180, type: "triangle", duration: 0.22, gain: 0.045 });
    },
    heard() {
      // Soft confirmation that the mic clip finished — before transcript text.
      tone({ freq: 520, type: "sine", duration: 0.07, gain: 0.05 });
      tone({ freq: 780, type: "sine", duration: 0.1, gain: 0.045, delay: 0.06 });
    },
  };

  window.jarvisSfx = sfx;

  // Unlock audio on first user gesture (Chromium autoplay policy).
  const unlock = () => {
    sfx.unlock();
    window.removeEventListener("pointerdown", unlock);
    window.removeEventListener("keydown", unlock);
  };
  window.addEventListener("pointerdown", unlock);
  window.addEventListener("keydown", unlock);
})();
