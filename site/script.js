// Parallax & interactions for CAT WARE site
(function(){
  const roots = document.querySelectorAll('.parallax');
  const hero = document.querySelector('.hero');
  const bounds = hero || document.body;
  function onMove(e){
    const rect = bounds.getBoundingClientRect();
    const cx = e.clientX - rect.left;
    const cy = e.clientY - rect.top;
    roots.forEach(el => {
      const depth = parseFloat(el.getAttribute('data-depth')||'6');
      const rx = ((cx/rect.width)-0.5) * depth;
      const ry = ((cy/rect.height)-0.5) * depth;
      el.style.transform = `translate3d(${rx}px, ${ry}px, 0)`;
    })
  }
  window.addEventListener('mousemove', onMove, {passive:true});

  // Ripple on buttons
  document.addEventListener('pointerdown', (e)=>{
    const t = e.target.closest('.ripple');
    if(!t) return;
    const rect = t.getBoundingClientRect();
    t.style.setProperty('--x', `${e.clientX-rect.left}px`);
    t.style.setProperty('--y', `${e.clientY-rect.top}px`);
  }, {passive:true});

  // Discord buttons
  function openDiscord(){
    const url = window.DISCORD_INVITE || 'https://discord.gg/btNXkxZTSU';
    window.open(url, '_blank', 'noopener');
  }
  ['discordBtn','discordBtn2','discordBtn3'].forEach(id=>{
    const el = document.getElementById(id);
    if(el){ el.addEventListener('click', openDiscord); }
  })

  // Year footer
  const y = document.getElementById('year');
  if(y){ y.textContent = new Date().getFullYear(); }

  // Cart badge updater (navbar)
  function updateCartBadge(){
    try{
      const el = document.getElementById('cartCount');
      if(!el) return;
      const raw = localStorage.getItem('catware_cart_v1') || '[]';
      const arr = JSON.parse(raw);
      el.textContent = String(Array.isArray(arr) ? arr.length : 0);
    }catch{}
  }
  updateCartBadge();

  // Snow background on hero
  const canvas = document.getElementById('fx-snow');
  if(canvas){
    const ctx = canvas.getContext('2d');
    let w, h, flakes = [];
    function resize(){
      w = canvas.width = canvas.offsetWidth;
      h = canvas.height = canvas.offsetHeight;
      // create flakes proportional to area
      const target = Math.min(200, Math.floor((w*h)/12000));
      flakes = Array.from({length: target}, ()=>({
        x: Math.random()*w,
        y: Math.random()*h,
        r: 1 + Math.random()*2.2,
        s: 0.6 + Math.random()*0.8, // speed
        o: 0.6 + Math.random()*0.4, // opacity
        drift: (Math.random()*0.6)-0.3
      }));
    }
    window.addEventListener('resize', resize);
    resize();

    function tick(){
      ctx.clearRect(0,0,w,h);
      ctx.fillStyle = 'rgba(255,255,255,0.9)';
      for(const f of flakes){
        ctx.globalAlpha = f.o;
        ctx.beginPath();
        ctx.arc(f.x, f.y, f.r, 0, Math.PI*2);
        ctx.fill();
        f.y += f.s; // fall
        f.x += f.drift; // lateral drift
        if(f.y > h+5){ f.y = -5; f.x = Math.random()*w; }
        if(f.x > w+5){ f.x = -5; }
        if(f.x < -5){ f.x = w+5; }
      }
      ctx.globalAlpha = 1;
      requestAnimationFrame(tick);
    }
    requestAnimationFrame(tick);
  }

  // Hero slider (rotate 3s)
  const slider = document.getElementById('heroSlider');
  if(slider){
    const imgs = Array.from(slider.querySelectorAll('img'));
    const prevBtn = slider.querySelector('.hs-prev');
    const nextBtn = slider.querySelector('.hs-next');
    const dotsWrap = slider.querySelector('.hs-dots');
    let idx = 0;
    function renderDots(){
      if(!dotsWrap) return;
      dotsWrap.innerHTML = imgs.map((_,i)=>`<button data-dot="${i}" aria-label="Go to slide ${i+1}"></button>`).join('');
    }
    function syncDots(){
      if(!dotsWrap) return;
      dotsWrap.querySelectorAll('button').forEach((b,i)=> b.classList.toggle('active', i===idx));
    }
    function show(i){ idx = i; imgs.forEach((im,k)=> im.classList.toggle('active', k===i)); syncDots(); }
    renderDots();
    dotsWrap?.addEventListener('click', (e)=>{
      const b = e.target.closest('button[data-dot]');
      if(!b) return;
      const n = Number(b.getAttribute('data-dot'))||0;
      show((n+imgs.length)%imgs.length);
      resetTimer();
    });
    // Mostra subito la prima immagine e poi avanza subito alla seconda per effetto immediato
    show(0);
    setTimeout(()=>{ idx = 1 % imgs.length; show(idx); }, 50);
    let t = setInterval(()=>{ idx = (idx+1)%imgs.length; show(idx); }, 3000);
    function resetTimer(){ clearInterval(t); t = setInterval(()=>{ idx = (idx+1)%imgs.length; show(idx); }, 3000); }
    if(prevBtn){ prevBtn.addEventListener('click', (e)=>{ e.preventDefault(); e.stopPropagation(); show((idx-1+imgs.length)%imgs.length); resetTimer(); }); }
    if(nextBtn){ nextBtn.addEventListener('click', (e)=>{ e.preventDefault(); e.stopPropagation(); show((idx+1)%imgs.length); resetTimer(); }); }

    // Delegated handlers in caso altri layer bloccano i click diretti
    document.addEventListener('click', (e)=>{
      const p = e.target.closest && e.target.closest('.hs-prev');
      if(!p) return;
      e.preventDefault();
      show((idx-1+imgs.length)%imgs.length);
      resetTimer();
    });
    document.addEventListener('click', (e)=>{
      const n = e.target.closest && e.target.closest('.hs-next');
      if(!n) return;
      e.preventDefault();
      show((idx+1)%imgs.length);
      resetTimer();
    });
  }

  // Global snow across entire site
  const gcanvas = document.getElementById('fx-snow-global');
  if(gcanvas){
    const gctx = gcanvas.getContext('2d');
    let gw=0, gh=0, gflakes=[];
    function gres(){
      gw = gcanvas.width = window.innerWidth;
      gh = gcanvas.height = window.innerHeight;
      const target = Math.min(400, Math.floor((gw*gh)/8000));
      if(gflakes.length < target){
        for(let i=gflakes.length;i<target;i++) gflakes.push({x:Math.random()*gw,y:Math.random()*gh,r:0.6+Math.random()*1.6,s:0.4+Math.random()*0.8,o:0.4+Math.random()*0.4,d:(Math.random()*0.5)-0.25});
      }else{
        gflakes = gflakes.slice(0, target);
      }
    }
    window.addEventListener('resize', gres);
    gres();
    (function loop(){
      gctx.clearRect(0,0,gw,gh);
      gctx.fillStyle = '#ffffff';
      for(const f of gflakes){
        gctx.globalAlpha = f.o;
        gctx.beginPath();
        gctx.arc(f.x, f.y, f.r, 0, Math.PI*2);
        gctx.fill();
        f.y += f.s;
        f.x += f.d;
        if(f.y>gh+4) { f.y=-4; f.x=Math.random()*gw; }
        if(f.x<-4) f.x=gw+4; else if(f.x>gw+4) f.x=-4;
      }
      gctx.globalAlpha = 1;
      requestAnimationFrame(loop);
    })();
  }

  // Reveal on scroll
  const reveals = document.querySelectorAll('.reveal');
  if(reveals.length){
    const io = new IntersectionObserver((entries)=>{
      entries.forEach(e=>{
        if(e.isIntersecting){ e.target.classList.add('reveal-in'); io.unobserve(e.target); }
      });
    }, {threshold: 0.12});
    reveals.forEach(el=> io.observe(el));
  }
})();
