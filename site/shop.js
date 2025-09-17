// Simple client-side cart + checkout demo
(function(){
  const CART_KEY = 'catware_cart_v1';
  const currency = (n)=>`€ ${Number(n).toFixed(2)}`;
  const plans = {
    cat_private: [
      {id:'cat_private_day', name:'1 Day', price:7},
      {id:'cat_private_week', name:'1 Week', price:20},
      {id:'cat_private_month', name:'1 Month', price:30},
      {id:'cat_private_life', name:'Lifetime', price:85},
    ],
    temp_spoofer: [
      {id:'temp_day', name:'1 Day', price:7},
      {id:'temp_week', name:'1 Week', price:22},
      {id:'temp_month', name:'1 Month', price:30},
      {id:'temp_life', name:'Lifetime', price:85},
    ],
    perm_spoofer: [
      {id:'perm_onetime', name:'One time', price:20},
      {id:'perm_life', name:'Lifetime', price:45},
    ],
  };
  const prodImages = {
    cat_private: 'assets/cat_private.jpg',
    temp_spoofer: 'assets/temp_spoofer.jpg',
    perm_spoofer: 'assets/perm_spoofer.jpg',
  };

  function loadCart(){
    try{ return JSON.parse(localStorage.getItem(CART_KEY)||'[]'); }catch{ return []; }
  }
  function saveCart(items){ localStorage.setItem(CART_KEY, JSON.stringify(items)); }
  function addItem(item){ const items = loadCart(); items.push(item); saveCart(items); }
  function totals(){ const items = loadCart(); return items.reduce((a,x)=>a+Number(x.price||0),0); }

  // Bind Buy buttons on index.html
  document.addEventListener('click', (e)=>{
    const btn = e.target.closest('.buy-btn');
    if(!btn) return;
    const item = {
      id: btn.dataset.id,
      name: btn.dataset.name,
      price: Number(btn.dataset.price||0)
    };
    addItem(item);
    window.location.href = 'cart.html';
  });
  // ensure CTA style on buy buttons
  document.querySelectorAll('.buy-btn').forEach(b=> b.classList.add('btn-cta'));
  // open product details modal
  const modal = document.getElementById('prodModal');
  const modalContent = document.getElementById('modalContent');
  function closeModal(){ if(modal){ modal.classList.remove('show'); document.body.classList.remove('modal-open'); } }
  function productDetails(pid){
    if(pid==='temp_spoofer'){
      return `
        <h4>Information</h4>
        <ul>
          <li>Supported Systems: Windows 10 & 11</li>
          <li>Supports FN Tournaments</li>
          <li>Supports ALL Motherboards</li>
        </ul>
        <h4>Why us?</h4>
        <ul>
          <li>FN Tournament Cleaner !</li>
          <li>Changes ALL HWID Identifiers !</li>
          <li>Built-in Cleaner.</li>
          <li>Fastest customer support in the market.</li>
          <li>Instant delivery.</li>
          <li>Detailed Instructions.</li>
          <li>Unlimited license resets.</li>
        </ul>
        <h4>Supported Motherboards</h4>
        <p>ASUS (STAYS AFTER REINSTALL!), MSI, Gigabyte, ASRock, EVGA, Biostar, Colorfull, Lenovo (Desktop Only), Acer (Desktop Only).</p>
        <h4>Supported Games</h4>
        <ul>
          <li>Fortnite</li>
          <li>EAC Games</li>
          <li>BE Games</li>
          <li>Rainbow 6 Siege</li>
          <li>Rust</li>
          <li>COD Game Series</li>
          <li>Game not listed here? We offer a lot more! Open a ticket and ask!</li>
        </ul>
      `;
    }
    if(pid==='perm_spoofer'){
      return `
        <h4>Supported Operating Systems</h4>
        <ul>
          <li>All Windows Versions Supported</li>
          <li>Processors Supported: Intel & AMD</li>
          <li>All Motherboards</li>
        </ul>
        <h4>Advanced Spoofing</h4>
        <ul>
          <li>Revert Spoof Option – Easily undo changes</li>
          <li>Persistent Spoofing – No HWID resets after Windows reinstall</li>
          <li>GPU Spoofing – Works across NVIDIA & AMD GPUs</li>
          <li>TPM Spoofing (Safe In Fortnite Tournaments)</li>
          <li>Permanent Ethernet Spoofing – No need for adapter resets</li>
          <li>HYPER-V Spoofing – Full virtualization spoofing</li>
          <li>Tourney-Safe Support – Works with competitive environments</li>
          <li>Win10 & Win11 Support – Fully compatible</li>
        </ul>
        <h4>Features & Capabilities</h4>
        <ul>
          <li>SMBIOS Fixer – Full serial & UUID spoofing</li>
          <li>Clean UI & User-Friendly Layout</li>
          <li>Undetected Disk Spoofing – Stays even after reboot</li>
          <li>No RAID0 Required</li>
          <li>Supports Every Motherboard</li>
          <li>Customized Serial Generation for Each System</li>
          <li>Built-in EFI Spoofing</li>
          <li>Custom EFI for Every User</li>
          <li>Advanced Driver Loading & Seeding System</li>
          <li>Seeding-Based Serials</li>
        </ul>
      `;
    }
    // cat_private
    return `
      <h4>Information</h4>
      <ul>
        <li>Windows 10 & 11 23H2 Supported</li>
        <li>Inbuilt Spoofer</li>
        <li>Works With TPM & Secure Boot Enabled</li>
        <li>Processors Supported: Intel & AMD</li>
        <li>Tournament & Ranked Ready</li>
      </ul>
      <h4>Aim</h4>
      <ul>
        <li>Memory Aim, Fov Circle, Target Switch Delay</li>
        <li>Visibility Check, Raytrace Visibility Check</li>
        <li>Aimkey, Aim Prediction, Ignore Knocked</li>
        <li>Aim Bone, Random Aim Bone</li>
        <li>Fov Size, Smoothing, Distance</li>
        <li>Controller Supported</li>
      </ul>
      <h4>Trigger</h4>
      <ul>
        <li>Enable / Disable, Trigger Key, Delay</li>
        <li>Shotgun Only</li>
      </ul>
      <h4>Weapon Configuration</h4>
      <ul>
        <li>Enable / Disable</li>
        <li>Select Weapon Class [Shotgun / SMG / Pistol / Rifle / Sniper]</li>
        <li>Adjustable FOV & Smooth</li>
        <li>Bone [Head / Neck / Spine / Pelvis / Nearest Bone]</li>
      </ul>
      <h4>Visuals</h4>
      <ul>
        <li>Box, Cornered Box, Filled Box</li>
        <li>Distance, Skeleton, Platform, Head Dot</li>
        <li>Aim Line, Snaplines, Name, Held Weapon, Rank</li>
        <li>Bot Check, Team Check, Skeleton Thickness</li>
      </ul>
      <h4>Radar</h4>
      <ul>
        <li>Enable / Disable</li>
        <li>Radar Distance, Position X/Y, Radar Size</li>
        <li>Ignore Bots</li>
      </ul>
      <h4>World</h4>
      <ul>
        <li>Enable/Disable</li>
        <li>Vehicles, Chests, Ammo Boxes, Floor Loot</li>
        <li>Distances per item type</li>
      </ul>
      <h4>Colors</h4>
      <ul>
        <li>Visible/Invisible Color, Skeleton Color, Text Color</li>
        <li>Fov Circle Color, Radar Color, Knocked/NPC/Team Color</li>
      </ul>
      <h4>Misc</h4>
      <ul>
        <li>Stretched Support, Stream Proof</li>
        <li>Config System (Load / Save)</li>
        <li>Controller Support, Vsync, FPS Counter</li>
      </ul>
    `;
  }

  function openDetails(pid){
    const list = plans[pid]||[];
    if(!modal || !modalContent || list.length===0) return;
    const title = pid==='cat_private'? 'Cat Ware Private' : pid==='temp_spoofer'? 'Temp Spoofer' : 'Perm Spoofer';
    const features = (
      pid==='cat_private' ? ['Private access','Fast updates','Support'] :
      pid==='temp_spoofer' ? ['Temporary serial spoof','Easy to use','Support'] :
      ['Permanent serial spoof','Works on many boards','Support']
    );
    const grid = list.map(p=>`<div class="card"><div class="card-body" style="display:flex;justify-content:space-between;align-items:center;gap:10px"><div><strong>${p.name}</strong><div class="note">${currency(p.price)}</div></div><button class="btn btn-primary btn-cta" data-add-variant="${p.id}" data-name="${title} - ${p.name}" data-price="${p.price}">Add to cart</button></div></div>`).join('');
    const img = prodImages[pid] || '';
    const hero = img ? `<div class="modal-hero"><img src="${img}" alt="${title}" onerror="this.parentElement.style.display='none'"/></div>` : '';
    modalContent.innerHTML = `
      <h2>${title}</h2>
      ${hero}
      <div class="note">Choose your plan</div>
      <div style="display:grid;grid-template-columns:1fr 1fr;gap:14px;margin:12px 0">${grid}</div>
      <h3>Product details</h3>
      <div class="details-rich">${productDetails(pid)}</div>
    `;
    modal.classList.add('show');
    document.body.classList.add('modal-open');
  }
  document.addEventListener('click', (e)=>{
    const close = e.target.closest('.modal-backdrop, .modal-close');
    if(close) closeModal();
  });
  document.addEventListener('click', (e)=>{
    const btn = e.target.closest('.open-details');
    if(!btn) return;
    const pid = btn.getAttribute('data-id');
    openDetails(pid);
  });
  // Direct binding too (in case delegation is blocked by other layers)
  document.querySelectorAll('.open-details').forEach(el=>{
    console.debug('[shop] bind open-details for', el.getAttribute('data-id'));
    el.addEventListener('click', (ev)=>{ ev.preventDefault(); ev.stopPropagation(); console.debug('[shop] click open-details'); openDetails(el.getAttribute('data-id')); });
  });
  // Fallback: click on whole product card
  document.querySelectorAll('article.product').forEach(card=>{
    card.addEventListener('click', (ev)=>{
      const btn = card.querySelector('.open-details');
      if(!btn) return;
      // If click was directly on a button, it is already handled
      if(ev.target.closest && ev.target.closest('.open-details')) return;
      console.debug('[shop] card click -> open details');
      openDetails(btn.getAttribute('data-id'));
    });
  });
  document.addEventListener('click', (e)=>{
    const add = e.target.closest('[data-add-variant]');
    if(!add) return;
    addItem({ id: add.getAttribute('data-add-variant'), name: add.getAttribute('data-name'), price: Number(add.getAttribute('data-price')) });
    closeModal();
    window.location.href = 'cart.html';
  });

  // Render cart on cart.html
  function renderCart(){
    const list = document.getElementById('cartItems');
    const empty = document.getElementById('cartEmpty');
    const summary = document.getElementById('cartSummary');
    if(!list || !empty || !summary) return;
    const items = loadCart();
    list.innerHTML = '';
    if(items.length === 0){
      empty.style.display = '';
      summary.style.display = 'none';
      return;
    }
    empty.style.display = 'none';
    summary.style.display = '';
    let html = '';
    items.forEach((it, idx)=>{
      html += `<div class="card"><div class="card-body" style="display:flex;align-items:center;justify-content:space-between;gap:10px"><div><strong>${it.name}</strong><div class="note">${currency(it.price)}</div></div><button class="btn btn-outline" data-remove="${idx}">Remove</button></div></div>`;
    });
    list.innerHTML = html;
    document.getElementById('cartTotal').textContent = currency(totals());
  }
  document.addEventListener('click', (e)=>{
    const rm = e.target.closest('[data-remove]');
    if(!rm) return;
    const items = loadCart();
    const idx = Number(rm.getAttribute('data-remove'));
    items.splice(idx,1);
    saveCart(items);
    renderCart();
  });

  // Render summary on checkout.html
  function renderCheckout(){
    const sum = document.getElementById('summary');
    const total = document.getElementById('total');
    const btn = document.getElementById('placeOrder');
    if(!sum || !total || !btn) return;
    const items = loadCart();
    sum.innerHTML = items.map(it=>`<div style="display:flex;justify-content:space-between"><span>${it.name}</span><span>${currency(it.price)}</span></div>`).join('');
    total.textContent = currency(totals());
    // Panels toggle by radio (support revolut + paypalme)
    function togglePanels(){
      const sel = document.querySelector('input[name="pay"]:checked')?.value || 'revolut';
      document.querySelectorAll('.pay-panel').forEach(p=> p.style.display = 'none');
      const el = document.getElementById(`panel-${sel}`);
      if(el) el.style.display = '';
    }
    document.querySelectorAll('input[name="pay"]').forEach(r=> r.addEventListener('change', togglePanels));
    togglePanels();

    // Payment settings (without editing files) using localStorage
    const inRev = document.getElementById('inRevolut');
    const inPme = document.getElementById('inPaypalMe');
    const inDirect = document.getElementById('inDirectLink');
    const saveBtn = document.getElementById('savePayCfg');
    try{
      const saved = JSON.parse(localStorage.getItem('catware_paycfg')||'{}');
      if(inRev && saved.revolut){ inRev.value = saved.revolut; window.REVOLUT_USER = saved.revolut; }
      if(inPme && saved.paypalme){ inPme.value = saved.paypalme; window.PAYPAL_ME = saved.paypalme; }
      if(inDirect && saved.direct){ inDirect.value = saved.direct; window.DIRECT_LINK = saved.direct; }
    }catch{}
    if(saveBtn){
      saveBtn.addEventListener('click', ()=>{
        const cfg = {
          revolut: (inRev && inRev.value || '').replace(/^@+/, ''),
          paypalme: (inPme && inPme.value || '').replace(/^@+/, ''),
          direct: (inDirect && inDirect.value || ''),
        };
        localStorage.setItem('catware_paycfg', JSON.stringify(cfg));
        window.REVOLUT_USER = cfg.revolut;
        window.PAYPAL_ME = cfg.paypalme;
        window.DIRECT_LINK = cfg.direct;
        alert('Impostazioni salvate.');
      });
    }

    // Checkout handler: revolut or paypalme
    btn.addEventListener('click', ()=>{
      const method = document.querySelector('input[name="pay"]:checked')?.value || 'revolut';
      const amount = totals().toFixed(2);
      const currencySel = document.getElementById('currency');
      const currency = (currencySel && currencySel.value) ? currencySel.value : 'EUR';
      if(method === 'paypalme'){
        const user = (window.PAYPAL_ME||'').trim();
        if(!user){ alert('Inserisci il tuo username PayPal.me nelle Impostazioni pagamento.'); return; }
        window.location.href = `https://www.paypal.me/${encodeURIComponent(user)}/${amount}`;
        return;
      }
      // Revolut
      const direct = (window.DIRECT_LINK||'').trim();
      if(direct){
        const url = direct.replace('{amount}', amount).replace('{currency}', currency);
        window.location.href = url;
      }else{
        const user = window.REVOLUT_USER || '';
        if(!user){ alert('Configura il tuo username Revolut (o inserisci un link diretto).'); return; }
        window.location.href = `https://revolut.me/${encodeURIComponent(user)}?amount=${amount}&currency=${encodeURIComponent(currency)}`;
      }
    });
  }

  // Initial renders depending on page
  // no enforcement; support both revolut and paypalme

  if(location.pathname.endsWith('/cart.html') || location.pathname.endsWith('cart.html')) renderCart();
  if(location.pathname.endsWith('/checkout.html') || location.pathname.endsWith('checkout.html')) renderCheckout();
})();
