// Injected with page.add_init_script() before the game loads. Playwright's video has no sound, so this copies
// everything the page plays through Web Audio (Unity WebGL, Howler, plain WebAudio) into a MediaRecorder.
// Read it back with: page.evaluate("window.__tapStop()") -> {b64, startedAt} (startedAt = ms since navigation start).
// Not tapped: <audio>/<video> elements (HTMLMediaElement). If a game uses those, the result is silent - check volume.
(() => {
  const AC = window.AudioContext || window.webkitAudioContext;
  if (!AC) return;
  const taps = new WeakMap();
  let rec = null, chunks = [], startedAt = null, mainDest = null;
  function tapFor(ctx) {
    let d = taps.get(ctx);
    if (!d) {
      d = ctx.createMediaStreamDestination();
      taps.set(ctx, d);
      if (!mainDest) {
        mainDest = d;
        rec = new MediaRecorder(d.stream, { mimeType: 'audio/webm;codecs=opus' });
        rec.ondataavailable = e => e.data.size && chunks.push(e.data);
        rec.start(1000);
        startedAt = performance.now();
      }
    }
    return d;
  }
  const connect = AudioNode.prototype.connect;
  AudioNode.prototype.connect = function (target, ...rest) {
    const r = connect.call(this, target, ...rest);
    if (target instanceof AudioDestinationNode) {
      try { connect.call(this, tapFor(this.context)); } catch (e) {}
    }
    return r;
  };
  window.__tapStop = () => new Promise(res => {
    if (!rec) return res({ b64: null, startedAt: null });
    rec.onstop = async () => {
      const buf = new Uint8Array(await new Blob(chunks, { type: 'audio/webm' }).arrayBuffer());
      let s = '';
      for (let i = 0; i < buf.length; i += 0x8000) s += String.fromCharCode.apply(null, buf.subarray(i, i + 0x8000));
      res({ b64: btoa(s), startedAt });
    };
    rec.stop();
  });
})();
