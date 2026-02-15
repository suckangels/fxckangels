const canvas = document.getElementById("particles");
const ctx = canvas.getContext("2d");

let w, h, dpr;

function resize(){
  dpr = Math.min(window.devicePixelRatio || 1, 2);
  w = canvas.width = Math.floor(window.innerWidth * dpr);
  h = canvas.height = Math.floor(window.innerHeight * dpr);
  canvas.style.width = window.innerWidth + "px";
  canvas.style.height = window.innerHeight + "px";
}
window.addEventListener("resize", resize);
resize();

const COUNT = 110;
const particles = Array.from({length: COUNT}).map(() => ({
  x: Math.random() * w,
  y: Math.random() * h,
  r: (Math.random() * 1.8 + 0.6) * dpr,
  vx: (Math.random() * 0.18 - 0.09) * dpr,
  vy: (Math.random() * 0.35 + 0.08) * dpr,
  a: Math.random() * 0.35 + 0.10
}));

function draw(){
  ctx.clearRect(0,0,w,h);

  // лёгкая дымка для мягкости
  ctx.fillStyle = "rgba(0,0,0,0.20)";
  ctx.fillRect(0,0,w,h);

  for(const p of particles){
    const glow = p.r * 5.2;

    const g = ctx.createRadialGradient(p.x, p.y, 0, p.x, p.y, glow);
    g.addColorStop(0, `rgba(255,255,255,${p.a})`);
    g.addColorStop(1, `rgba(255,255,255,0)`);

    ctx.fillStyle = g;
    ctx.beginPath();
    ctx.arc(p.x, p.y, glow, 0, Math.PI * 2);
    ctx.fill();

    p.x += p.vx;
    p.y += p.vy;

    if (p.y > h + 60*dpr){
      p.y = -60*dpr;
      p.x = Math.random() * w;
    }
    if (p.x < -80*dpr) p.x = w + 80*dpr;
    if (p.x > w + 80*dpr) p.x = -80*dpr;
  }

  requestAnimationFrame(draw);
}
draw();
