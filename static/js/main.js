/* ================= HELPERS ================= */
const $  = s => document.querySelector(s);
const $$ = s => [...document.querySelectorAll(s)];

const fine = matchMedia('(hover:hover)').matches;   // currently unused


/* ================= MARQUEE TEXT ================= */
const words = ['Reuse', 'Repair', 'Recycle', 'Donate', 'Exchange', 'Sell', 'Swap', 'Renew'];

if ($('#mq')) {
  $('#mq').innerHTML = Array(4)
    .fill(words.map(w => w + ' ✦ ').join(''))
    .join('');
}


/* ================= SPLIT HEADLINE INTO LETTERS ================= */
const title = $('#title');
let letterIndex = 0;

if (title) {
  title.innerHTML = title.textContent
    .split(' ')
    .map(word =>
      '<span style="display:inline-block;white-space:nowrap">' +
        [...word]
          .map(ch => `<span style="animation-delay:${(letterIndex++) * .035}s">${ch}</span>`)
          .join('') +
      '</span>'
    )
    .join(' ');
}


/* ================= CURSOR + PARTICLE TRAIL ================= */
const dot  = $('#dot');
const ring = $('#ring');
const cv   = $('#trail');
const cx   = cv.getContext('2d');

let mx = innerWidth / 2;
let my = innerHeight / 2;
let rx = mx;
let ry = my;
let parts = [];

function size() {
  cv.width  = innerWidth;
  cv.height = innerHeight;
}
size();
addEventListener('resize', size);

addEventListener('mousemove', e => {
  mx = e.clientX;
  my = e.clientY;
  dot.style.left = mx + 'px';
  dot.style.top  = my + 'px';

  // Spawn 2 particles per mouse move
  for (let i = 0; i < 2; i++) {
    parts.push({
      x: mx,
      y: my,
      vx: (Math.random() - .5) * 2,
      vy: (Math.random() - .5) * 2 - .6,
      l: 1,                                   // life
      r: 3 + Math.random() * 5,               // radius
      c: Math.random() > .5 ? '46,139,87' : '255,200,61'
    });
  }

  // Parallax for floating emojis: elements with data-s="strength"
  const hero = $('#hero');
  if (hero) {
    const dx = (mx / innerWidth  - .5);
    const dy = (my / innerHeight - .5);

    $$('[data-s]').forEach(el => {
      const s = +el.dataset.s;
      el.style.transform = `translate(${dx * s * 2}px, ${dy * s * 2}px)`;
    });
  }
});

// Animation loop: ring follows the mouse, particles fade out
(function loop() {
  rx += (mx - rx) * .15;
  ry += (my - ry) * .15;
  ring.style.left = rx + 'px';
  ring.style.top  = ry + 'px';

  cx.clearRect(0, 0, cv.width, cv.height);
  parts = parts.filter(p => p.l > 0);

  parts.forEach(p => {
    p.x += p.vx;
    p.y += p.vy;
    p.l -= .025;

    cx.fillStyle = `rgba(${p.c}, ${p.l * .6})`;
    cx.beginPath();
    cx.arc(p.x, p.y, p.r * p.l, 0, 7);
    cx.fill();
  });

  requestAnimationFrame(loop);
})();

// Ring grows over links and buttons
document.addEventListener('mouseover', e => {
  ring.classList.toggle('big', !!e.target.closest('a,button'));
});


/* ================= MAGNETIC BUTTONS ================= */
// Add data-mag to any button/link you want pulled toward the mouse
$$('[data-mag]').forEach(b => {
  b.addEventListener('mousemove', e => {
    const r = b.getBoundingClientRect();
    const x = (e.clientX - r.left - r.width  / 2) * .3;
    const y = (e.clientY - r.top  - r.height / 2) * .4;
    b.style.transform = `translate(${x}px, ${y}px)`;
  });

  b.addEventListener('mouseleave', () => {
    b.style.transform = '';
  });
});


/* ================= 3D TILT + SPOTLIGHT CARDS ================= */
if ($('#grid')) {
  $('#grid').addEventListener('mousemove', e => {
    const c = e.target.closest('.card');
    if (!c) return;

    const r = c.getBoundingClientRect();
    const x = (e.clientX - r.left) / r.width;
    const y = (e.clientY - r.top)  / r.height;

    c.style.transform =
      `rotateY(${(x - .5) * 16}deg) rotateX(${(.5 - y) * 16}deg) translateY(-6px)`;
    c.style.setProperty('--mx', x * 100 + '%');
    c.style.setProperty('--my', y * 100 + '%');
  });

  $('#grid').addEventListener('mouseout', e => {
    const c = e.target.closest('.card');
    if (c) c.style.transform = '';
  });
}


/* ================= NAV SLIDING PILL ================= */
const pill = $('#pill');

$$('#links a').forEach(a => {
  a.addEventListener('mouseenter', () => {
    pill.style.opacity = 1;
    pill.style.left    = a.offsetLeft + 'px';
    pill.style.width   = a.offsetWidth + 'px';
  });
});

$('#links').addEventListener('mouseleave', () => {
  pill.style.opacity = 0;
});


/* ================= TABS ================= */
const tb = $$('#tabs button');
const tp = $('#tabpill');
const pn = $$('.panel');

function pick(i) {
  tb.forEach((b, j) => b.classList.toggle('on', i === j));
  pn.forEach((p, j) => p.classList.toggle('on', i === j));
  tp.style.left  = tb[i].offsetLeft + 'px';
  tp.style.width = tb[i].offsetWidth + 'px';
}

tb.forEach((b, i) => b.onclick = () => pick(i));

addEventListener('load', () => {
  if (tb.length) pick(0);
});


/* ================= SCROLL: PROGRESS BAR, NAV HIDE, STEPS LINE ================= */
let lastY = 0;

addEventListener('scroll', () => {
  const y = scrollY;
  const h = document.documentElement.scrollHeight - innerHeight;

  // Top progress bar
  $('#bar').style.width = (y / h * 100) + '%';

  // Hide nav when scrolling down, show when scrolling up
  $('#nav').classList.toggle('hide', y > lastY && y > 200);
  lastY = y;

  // Timeline fill
  const st = $('#steps');
  if (st) {
    const s = st.getBoundingClientRect();
    const p = Math.max(0, Math.min(100, (innerHeight * .6 - s.top) / s.height * 100));
    st.style.setProperty('--p', p + '%');
  }
}, { passive: true });


/* ================= SCROLL REVEAL + COUNTERS ================= */
const io = new IntersectionObserver(entries => {
  entries.forEach(e => {
    if (!e.isIntersecting) return;

    e.target.classList.add('show');
    io.unobserve(e.target);

    // Count up any [data-c] number inside the revealed element
    const c = e.target.querySelector('[data-c]');
    if (c) {
      const to = +c.dataset.c;
      let v = 0;

      if (to > 0) {
        const k = setInterval(() => {
          v++;
          c.textContent = v;
          if (v >= to) clearInterval(k);
        }, 120);
      }
    }
  });
}, { threshold: .2 });

$$('.rv').forEach(el => io.observe(el));


/* ================= PAGE TRANSITIONS (WIPE) ================= */
const w = $('#wipe');
w.classList.add('out');                       // wipe away on page load

$$('a[href^="/"]').forEach(a => {
  a.addEventListener('click', e => {
    if (e.metaKey || e.ctrlKey) return;       // allow open-in-new-tab

    e.preventDefault();
    w.classList.remove('out');
    w.classList.add('in');                    // wipe in, then navigate
    setTimeout(() => location.href = a.href, 550);
  });
});

// Back/forward cache: reset the wipe so the page isn't covered
addEventListener('pageshow', e => {
  if (e.persisted) w.className = '';
});