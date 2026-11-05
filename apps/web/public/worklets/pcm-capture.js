// Live interview capture: microphone audio → 16 kHz mono 16-bit PCM, posted to the main
// thread about ten times a second. Runs on the audio thread (AudioWorklet).
const TARGET_RATE = 16000;
const CHUNK = 1600; // 100 ms at 16 kHz

class PcmCapture extends AudioWorkletProcessor {
  constructor() {
    super();
    this.step = sampleRate / TARGET_RATE; // input samples per output sample
    this.pos = 0; // position of the next output sample, in input samples
    this.prev = 0; // last input sample of the previous block, for interpolation
    this.out = new Int16Array(CHUNK);
    this.filled = 0;
  }

  process(inputs) {
    const channels = inputs[0];
    if (!channels || channels.length === 0) return true;
    const n = channels[0].length;
    // Mix to mono.
    const mono = new Float32Array(n);
    for (const ch of channels) for (let i = 0; i < n; i++) mono[i] += ch[i] / channels.length;
    // Linear-interpolation resampling. Speech sits well below 8 kHz, so this is enough.
    while (this.pos < n) {
      const i = Math.floor(this.pos);
      const frac = this.pos - i;
      const a = i === 0 ? this.prev : mono[i - 1];
      const b = mono[i];
      const s = Math.max(-1, Math.min(1, a + (b - a) * frac));
      this.out[this.filled++] = s < 0 ? s * 0x8000 : s * 0x7fff;
      if (this.filled === CHUNK) {
        this.port.postMessage(this.out.buffer, [this.out.buffer]);
        this.out = new Int16Array(CHUNK);
        this.filled = 0;
      }
      this.pos += this.step;
    }
    this.pos -= n;
    this.prev = mono[n - 1];
    return true;
  }
}

registerProcessor("pcm-capture", PcmCapture);
