/* FLARE-X living galaxy: one fixed canvas behind every page. No libraries.
   Layers: nebula clouds, 3 parallax star layers (twinkle + drift), a slowly rotating spiral galaxy, shooting stars,
   and the "ghostly blue flame sphere" of a microgravity flame (breathing, with orbiting sparks).
   Respects prefers-reduced-motion (one still frame), pauses when the tab is hidden, and lowers quality if the device is slow. */
(function () {
  "use strict";
  var reduce = window.matchMedia && matchMedia("(prefers-reduced-motion: reduce)").matches;
  var cv = document.createElement("canvas"); cv.id = "galaxy"; cv.setAttribute("aria-hidden", "true");
  document.body.insertBefore(cv, document.body.firstChild);
  var ctx = cv.getContext("2d"); if (!ctx) return;

  function prng(seed) { return function () { seed |= 0; seed = seed + 0x6D2B79F5 | 0; var t = Math.imul(seed ^ seed >>> 15, 1 | seed); t = t + Math.imul(t ^ t >>> 7, 61 | t) ^ t; return ((t ^ t >>> 14) >>> 0) / 4294967296; }; }
  var rnd = prng(20261114), W = 0, H = 0, DPR = 1, Q = 1, stars = [], arms = [], shoot = [], nextShoot = 2500;
  var mouse = { x: 0, y: 0, tx: 0, ty: 0 }, sy = 0, raf = 0, slow = 0, lastT = 0, running = false;
  var TINT = [[255, 255, 255], [207, 227, 255], [158, 198, 255], [255, 217, 194]];
  var LAYERS = [{ d: 1500, r: [0.55, 1.05], a: [0.3, 0.7], v: 0.006, p: 0.012 }, { d: 4800, r: [0.9, 1.6], a: [0.45, 0.9], v: 0.012, p: 0.03 }, { d: 20000, r: [1.2, 2.2], a: [0.65, 1], v: 0.022, p: 0.06 }];
  var BLOBS = [{ x: .18, y: .25, r: .62, c: [11, 61, 145], a: .30, s: .00005, p: 0 }, { x: .82, y: .7, r: .66, c: [96, 44, 160], a: .17, s: .00004, p: 2 },
               { x: .55, y: .08, r: .48, c: [252, 61, 33], a: .06, s: .00006, p: 4 }, { x: .08, y: .88, r: .55, c: [30, 120, 210], a: .15, s: .00005, p: 1 }];

  var glow = document.createElement("canvas"); glow.width = glow.height = 48;           // reusable soft sprite for bright stars
  (function () { var g = glow.getContext("2d"), r = g.createRadialGradient(24, 24, 0, 24, 24, 24); r.addColorStop(0, "rgba(255,255,255,1)"); r.addColorStop(.25, "rgba(200,225,255,.45)"); r.addColorStop(1, "rgba(200,225,255,0)"); g.fillStyle = r; g.fillRect(0, 0, 48, 48); })();

  function build() {
    stars = []; var area = W * H;
    LAYERS.forEach(function (L, li) {
      var n = Math.round(area / L.d * Q);
      for (var i = 0; i < n; i++) stars.push({ l: li, x: rnd() * W, y: rnd() * H, r: L.r[0] + rnd() * (L.r[1] - L.r[0]), a: L.a[0] + rnd() * (L.a[1] - L.a[0]), ph: rnd() * 6.28, sp: .6 + rnd() * 1.6, c: TINT[Math.floor(rnd() * TINT.length)] });
    });
    arms = []; var N = Math.round(1500 * Q);
    for (var k = 0; k < N; k++) { var d = Math.pow(rnd(), .62), arm = k % 2, ang = d * 4.4 + arm * Math.PI + (rnd() - .5) * .5 * (1 - d * .5);
      arms.push({ ang: ang, rad: d, off: (rnd() - .5) * .07, b: .25 + .75 * (1 - d) + rnd() * .2, s: .5 + rnd() * 1.1 }); }
  }
  function resize() {
    W = window.innerWidth || 1280; H = window.innerHeight || 800; DPR = Math.min(window.devicePixelRatio || 1, 2);
    cv.width = Math.round(W * DPR); cv.height = Math.round(H * DPR); cv.style.width = W + "px"; cv.style.height = H + "px";
    ctx.setTransform(DPR, 0, 0, DPR, 0, 0); build(); draw(lastT);
  }
  var wrap = function (v, m) { return ((v % m) + m) % m; };

  function draw(t) {
    lastT = t; mouse.x += (mouse.tx - mouse.x) * .05; mouse.y += (mouse.ty - mouse.y) * .05;
    ctx.globalCompositeOperation = "source-over"; ctx.fillStyle = "#03060c"; ctx.fillRect(0, 0, W, H);
    var big = Math.max(W, H), i, s, g;
    ctx.globalCompositeOperation = "lighter";                                              // nebula clouds
    for (i = 0; i < BLOBS.length; i++) { var b = BLOBS[i], bx = (b.x + .05 * Math.sin(t * b.s * 1000 + b.p)) * W - sy * .02, by = (b.y + .04 * Math.cos(t * b.s * 800 + b.p)) * H;
      g = ctx.createRadialGradient(bx, by, 0, bx, by, b.r * big); g.addColorStop(0, "rgba(" + b.c + "," + b.a + ")"); g.addColorStop(.55, "rgba(" + b.c + "," + b.a * .35 + ")"); g.addColorStop(1, "rgba(" + b.c + ",0)"); ctx.fillStyle = g; ctx.fillRect(0, 0, W, H); }
    if (Q > .4) {                                                                           // distant spiral galaxy
      var cx = W * .14 - sy * .01 + mouse.x * 14, cy = H * .8 + mouse.y * 10, R = Math.min(W * .36, H * .62), rot = t * .000018, tilt = .42;
      g = ctx.createRadialGradient(cx, cy, 0, cx, cy, R * .5); g.addColorStop(0, "rgba(255,226,190,.5)"); g.addColorStop(.4, "rgba(150,185,255,.15)"); g.addColorStop(1, "rgba(150,185,255,0)"); ctx.fillStyle = g; ctx.fillRect(cx - R, cy - R, R * 2, R * 2);
      for (i = 0; i < arms.length; i++) { s = arms[i]; var a = s.ang + rot, rr = (s.rad + s.off) * R, px = Math.cos(a) * rr, py = Math.sin(a) * rr * tilt, x = cx + px * Math.cos(-.35) - py * Math.sin(-.35), y = cy + px * Math.sin(-.35) + py * Math.cos(-.35);
        var tw = .8 + .2 * Math.sin(t * .002 * s.s + i); ctx.fillStyle = s.rad < .3 ? "rgba(255,230,200," + (.75 * s.b * tw) + ")" : "rgba(160,195,255," + (.62 * s.b * tw) + ")"; ctx.fillRect(x, y, s.s * 1.25, s.s * 1.25); } }
    for (i = 0; i < stars.length; i++) {                                                    // stars: twinkle, drift, parallax
      s = stars[i]; var L = LAYERS[s.l], x = wrap(s.x + mouse.x * L.p * 60, W), y = wrap(s.y - t * L.v * .06 - sy * L.p * .9 + mouse.y * L.p * 60, H);
      var al = s.a * (.62 + .38 * Math.sin(t * .001 * s.sp * 3 + s.ph));
      if (s.l === 2 && s.r > 1.35) { ctx.globalAlpha = al * .85; ctx.drawImage(glow, x - s.r * 5, y - s.r * 5, s.r * 10, s.r * 10); }
      ctx.globalAlpha = al; ctx.fillStyle = "rgb(" + s.c + ")"; ctx.fillRect(x - s.r / 2, y - s.r / 2, s.r, s.r);
    }
    ctx.globalAlpha = 1;
    var ox = W * (W < 760 ? .78 : .84) + mouse.x * -26, oy = H * .22 - sy * .05 + mouse.y * -18, r0 = Math.max(54, Math.min(150, Math.min(W, H) * (W < 760 ? .09 : .115)));
    var br = 1 + .06 * Math.sin(t * .0013) + .025 * Math.sin(t * .0037), R0 = r0 * br;     // the microgravity flame: a ghostly blue sphere
    g = ctx.createRadialGradient(ox, oy, R0 * .2, ox, oy, R0 * 2.8); g.addColorStop(0, "rgba(90,150,255,.16)"); g.addColorStop(1, "rgba(90,150,255,0)"); ctx.fillStyle = g; ctx.fillRect(ox - R0 * 3, oy - R0 * 3, R0 * 6, R0 * 6);
    g = ctx.createRadialGradient(ox, oy, 0, ox, oy, R0); g.addColorStop(0, "rgba(200,230,255,.78)"); g.addColorStop(.35, "rgba(105,165,255,.42)"); g.addColorStop(.7, "rgba(50,95,255,.15)"); g.addColorStop(1, "rgba(40,80,255,0)"); ctx.fillStyle = g; ctx.beginPath(); ctx.arc(ox, oy, R0, 0, 6.2832); ctx.fill();
    ctx.strokeStyle = "rgba(150,200,255,.14)"; ctx.lineWidth = 1; ctx.beginPath(); ctx.arc(ox, oy, R0 * .82, 0, 6.2832); ctx.stroke();
    for (i = 0; i < 12; i++) { var oa = t * .00035 * (.6 + i % 4 * .25) * (i % 2 ? 1 : -1) + i * .52, orr = R0 * (1.12 + (i % 5) * .13), fl = .5 + .5 * Math.sin(t * .004 + i * 1.7);
      ctx.fillStyle = "rgba(190,225,255," + (.25 + .55 * fl) + ")"; ctx.beginPath(); ctx.arc(ox + Math.cos(oa) * orr, oy + Math.sin(oa) * orr * .86, 1 + fl * 1.3, 0, 6.2832); ctx.fill(); }
    ctx.globalCompositeOperation = "source-over";
    for (i = shoot.length - 1; i >= 0; i--) {                                              // shooting stars
      var m = shoot[i], k = (t - m.t0) / m.life; if (k >= 1) { shoot.splice(i, 1); continue; }
      var hx = m.x + Math.cos(m.a) * m.v * (t - m.t0) / 1000, hy = m.y + Math.sin(m.a) * m.v * (t - m.t0) / 1000, tx = hx - Math.cos(m.a) * m.len, ty = hy - Math.sin(m.a) * m.len, f = Math.sin(k * Math.PI);
      g = ctx.createLinearGradient(hx, hy, tx, ty); g.addColorStop(0, "rgba(255,255,255," + .9 * f + ")"); g.addColorStop(1, "rgba(120,180,255,0)"); ctx.strokeStyle = g; ctx.lineWidth = 1.6; ctx.beginPath(); ctx.moveTo(hx, hy); ctx.lineTo(tx, ty); ctx.stroke(); }
  }
  function frame(now) {
    if (!running) return;
    if (lastT && now - lastT > 34) { if (++slow > 40 && Q > .3) { Q = Q > .6 ? .55 : .3; slow = 0; build(); } } else if (slow > 0) slow--;
    if (now > nextShoot) { shoot.push({ x: (.1 + rnd() * .8) * W, y: rnd() * H * .4, a: .3 + rnd() * .3 + (rnd() > .5 ? 0 : 1.9), v: 900 + rnd() * 500, len: 120 + rnd() * 90, t0: now, life: 700 + rnd() * 500 }); nextShoot = now + 4500 + rnd() * 6000; }
    draw(now); raf = requestAnimationFrame(frame);
  }
  function start() { if (reduce || running) return; running = true; raf = requestAnimationFrame(frame); }
  function stop() { running = false; cancelAnimationFrame(raf); }
  window.addEventListener("resize", resize);
  window.addEventListener("pointermove", function (e) { mouse.tx = e.clientX / W - .5; mouse.ty = e.clientY / H - .5; }, { passive: true });
  window.addEventListener("scroll", function () { sy = window.scrollY || 0; if (reduce) draw(lastT); }, { passive: true });
  document.addEventListener("visibilitychange", function () { document.hidden ? stop() : start(); });
  resize(); start();
  window.__galaxy = { canvas: cv, draw: draw, stats: function () { return { stars: stars.length, arms: arms.length, quality: Q, animated: running, shooting: shoot.length }; } };
})();
