let appliedCoupon = '';
'use strict';
const $ = id => document.getElementById(id);
const esc = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const money = value => new Intl.NumberFormat('es-CL', {style:'currency',currency:'CLP',maximumFractionDigits:0}).format(value);
const dateTime = value => new Date(value).toLocaleString('es-CL');
async function api(path, method='GET', data) {
    let response;
    try {
        response = await fetch(path, {method, credentials:'same-origin', headers: data === undefined ? {} : {'Content-Type':'application/json','X-3Dedos-Request':'1'}, body:data === undefined ? undefined : JSON.stringify(data)});
    } catch (_) { throw new Error('No hay conexión con la tienda. Comprueba que el servidor esté abierto y vuelve a intentar.'); }
    let result;
    try { result = await response.json(); } catch (_) { throw new Error('No se pudo leer la respuesta del servidor.'); }
    if (!response.ok) throw new Error(result.error || 'No se pudo completar la operación.');
    return result;
}
function notice(message, error=false) {
    const box = $('notice');
    box.textContent = message;
    box.className = 'notice' + (error ? ' notice-error' : '');
    clearTimeout(notice.timer);
    notice.timer = setTimeout(() => box.classList.add('hidden'), 6000);
}
let modalReturnFocus;
function showDialog(id) {
    document.querySelectorAll('.modal-shell').forEach(el => el.classList.add('hidden'));
    modalReturnFocus = document.activeElement;
    $(id).classList.remove('hidden');
    document.body.style.overflow = 'hidden';
    $(id).querySelector('input:not([hidden]), button, a')?.focus();
}
function hideDialog(id) {
    $(id).classList.add('hidden');
    document.body.style.overflow = '';
    modalReturnFocus?.focus();
}
document.addEventListener('keydown', event => {
    const dialog = document.querySelector('.modal-shell:not(.hidden)');
    if (!dialog) return;
    if (event.key === 'Escape') hideDialog(dialog.id);
    if (event.key === 'Tab') {
        const controls = [...dialog.querySelectorAll('button, input, select, a[href], [tabindex="0"]')].filter(el => !el.disabled && el.getClientRects().length);
        const first = controls[0], last = controls[controls.length - 1];
        if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last?.focus(); }
        else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first?.focus(); }
    }
});
document.addEventListener('click', event => {
    const close = event.target.closest('[data-close]');
    if (close) hideDialog(close.dataset.close);
    if (event.target.classList.contains('modal-shell')) hideDialog(event.target.id);
});
function orderMarkup(order, admin=false) {
    return `<article class="order-card"><div class="row between wrap"><h3>${esc(order.numero)} ${order.referencia_demo ? `<span class="badge">Registro ${esc(order.referencia_demo)}</span>` : ''}</h3><span class="badge ${order.estado === 'cancelado' ? 'muted' : ''}">${order.estado === 'cancelado' ? 'Cancelado' : 'Pendiente de pago'}</span></div>
        <p class="help">${esc(dateTime(order.fecha))}${admin ? ` · ${esc(order.cliente)} · ${esc(order.email)}` : ''}</p>
        <ul class="order-lines">${order.detalle.map(d => `<li><span>${esc(d.nombre)} × ${d.cantidad}<small>${money(d.precio_unitario)} por unidad</small></span><strong>${money(d.subtotal)}</strong></li>`).join('')}</ul>
        ${order.descuento ? `<div class="row between"><span>Descuento de bienvenida (20%)</span><strong>−${money(order.descuento)}</strong></div>` : ''}<div class="row between"><strong>Total</strong><strong class="order-total">${money(order.total)}</strong></div>
        ${admin && order.estado !== 'cancelado' ? `<button class="ui-button secondary small" data-cancel-order="${order.id}">Cancelar pedido ${esc(order.numero)}</button>` : ''}</article>`;
}

let productos = [], sagas = [], usuarioActual = null, configureAdmin = false, authMode = 'login';
let cart = [];
try {
    const stored = JSON.parse(sessionStorage.getItem('3dedos-carrito') || '[]');
    if (Array.isArray(stored)) cart = stored.filter(x => Number.isInteger(x.producto_id) && Number.isInteger(x.cantidad) && x.cantidad > 0 && x.cantidad <= 99);
} catch (_) { cart = []; }
let orderKey = null;
try { orderKey = sessionStorage.getItem('3dedos-solicitud'); } catch (_) {}
function persistCart(changed=true) {
    if (changed) orderKey = null;
    try {
        sessionStorage.setItem('3dedos-carrito', JSON.stringify(cart));
        if (orderKey) sessionStorage.setItem('3dedos-solicitud', orderKey);
        else sessionStorage.removeItem('3dedos-solicitud');
    } catch (_) {}
    if ($('cartCount')) $('cartCount').textContent = cart.reduce((sum,x) => sum+x.cantidad,0);
}
async function refreshShop() {
    const [init, items, events, instagram] = await Promise.all([api('/api/inicio'), api('/api/productos'), api('/api/eventos'), api('/api/instagram')]);
    usuarioActual = init.usuario; configureAdmin = init.configurar_admin; sagas = init.sagas; productos = items;
    $('preferenciaSaga').innerHTML = sagas.map(s => `<option value="${s.id}">${esc(s.nombre)}</option>`).join('');
    $('userInfo').textContent = usuarioActual ? `Hola, ${usuarioActual.nombre || 'Administrador'} 🎮` : '';
    $('userInfo').classList.toggle('hidden', !usuarioActual);
    $('authBtn').textContent = usuarioActual ? 'Cerrar Sesión' : 'Iniciar Sesión / Registro';
    $('ordersBtn').classList.toggle('hidden', usuarioActual?.rol !== 'cliente');
    $('adminLink').classList.toggle('hidden', usuarioActual?.rol !== 'admin' && !configureAdmin);
    $('adminLink').textContent = configureAdmin ? 'Configurar administración' : 'Administración';
    renderCatalog(); renderInstagram(instagram); renderEvents(events); persistCart(false);
}
function renderCatalog() {
    const list = [...productos];
    if (usuarioActual?.saga_id) {
        list.sort((a,b) => (b.saga_id === usuarioActual.saga_id) - (a.saga_id === usuarioActual.saga_id));
        const favorite = sagas.find(s => s.id === usuarioActual.saga_id);
        $('recSubtitle').textContent = `Mostrando primero los productos de tu saga favorita: ${favorite?.nombre || ''}`;
    } else $('recSubtitle').textContent = 'Inicia sesión para personalizar el orden de las recomendaciones según tus franquicias favoritas.';
    $('catalogGrid').innerHTML = list.map(p => {
        const favorite = usuarioActual?.saga_id === p.saga_id;
        return `<div class="bg-white rounded-2xl p-5 border-2 ${favorite ? 'border-brandYellow glow-yellow' : 'border-slate-200'} flex flex-col justify-between hover:border-brandPurple transition shadow-sm relative">
            ${favorite ? '<span class="absolute top-3 right-3 bg-brandYellow text-brandPurpleDark font-black text-[10px] px-2 py-0.5 rounded-full uppercase shadow">Recomendado</span>' : ''}
            <div class="product-media mb-4">${p.imagen ? `<img src="${esc(p.imagen)}" alt="${esc(p.nombre)}" loading="lazy" decoding="async">` : '<span>Sin imagen</span>'}</div>
            <div><span class="text-[10px] uppercase font-bold text-brandPurple bg-purple-100 border border-purple-300 px-2.5 py-1 rounded-full inline-block mb-1">${esc(p.nombre_saga)}</span>
            <h3 class="font-black text-slate-900 text-base mt-1">${esc(p.nombre)}</h3><p class="text-brandPurple font-black text-xl mt-2">${money(p.precio)}</p>
            <p class="help stock">${p.stock > 0 ? `${p.stock} disponibles` : 'Agotado'}</p></div>
            <button class="mt-4 w-full bg-brandPurple hover:bg-brandPurpleDark text-white py-2.5 rounded-xl text-xs font-extrabold transition shadow" data-add="${p.id}" ${p.stock === 0 ? 'disabled' : ''}>${p.stock > 0 ? 'Añadir al Carrito' : 'Sin stock'}</button></div>`;
    }).join('') || '<p>No hay productos disponibles por el momento.</p>';
}
function renderEvents(events) {
    $('eventsGrid').innerHTML = events.map(e => `<div class="bg-white p-6 rounded-2xl border-2 border-slate-200 hover:border-brandYellow transition space-y-3 relative overflow-hidden group shadow-sm">
        <div class="absolute top-0 right-0 w-2 h-full bg-brandPurple group-hover:bg-brandYellow transition"></div>
        <span class="bg-brandPurple text-white text-xs px-3 py-1 rounded-full font-bold inline-block">${esc(new Date(e.fecha+'T12:00:00').toLocaleDateString('es-CL',{day:'2-digit',month:'short',year:'numeric'}).toUpperCase())}</span>
        <h3 class="font-black text-lg text-slate-900">${esc(e.nombre)}</h3><p class="text-xs text-slate-600"><strong>Ubicación:</strong> ${esc(e.ubicacion)}</p>
        <p class="text-xs text-brandPurpleDark font-bold bg-purple-50 p-2 rounded-lg border border-purple-200">${esc(e.detalle)}</p></div>`).join('') || '<p>Pronto anunciaremos nuevas fechas.</p>';
}
function instagramEmbedUrl(link) {
    try {
        const url = new URL(link);
        if (!/(^|\.)instagram\.com$/i.test(url.hostname)) return null;
        const match = url.pathname.match(/^\/(p|reel|tv)\/([A-Za-z0-9_-]+)/i);
        return match ? `https://www.instagram.com/${match[1]}/${match[2]}/embed/captioned/` : null;
    } catch (_) { return null; }
}
function renderInstagram(posts) {
    const grid = $('instagramGrid');
    grid.innerHTML = posts.map(post => {
        const embed = instagramEmbedUrl(post.enlace);
        return `<article class="instagram-post"><iframe title="Publicación de Instagram: ${esc(post.titulo)}" src="${esc(embed || post.enlace)}" loading="lazy" allowtransparency="true" referrerpolicy="strict-origin-when-cross-origin"></iframe><div class="instagram-post-info"><h3>${esc(post.titulo)}</h3>${post.descripcion ? `<p>${esc(post.descripcion)}</p>` : ''}<a href="${esc(post.enlace)}" target="_blank" rel="noopener noreferrer">Abrir en Instagram ↗</a></div></article>`;
    }).join('') || '<p class="empty">Pronto compartiremos nuestras últimas creaciones.</p>';
}
function setAuthMode(mode) {
    authMode = mode;
    $('authTitle').textContent = mode === 'register' ? 'Crear mi cuenta' : mode === 'setup' ? 'Configurar administrador' : 'Iniciar sesión';
    $('authDescription').textContent = mode === 'setup' ? 'Crea la cuenta que administrará esta tienda local. Esta configuración se realiza una sola vez.' : 'Conserva tus pedidos y personaliza tus recomendaciones.';
    $('registrationFields').classList.toggle('hidden', mode !== 'register');
    $('username').required = mode === 'register';
    $('authPassword').autocomplete = mode === 'login' ? 'current-password' : 'new-password';
    $('authSubmit').textContent = mode === 'register' ? 'Crear cuenta' : mode === 'setup' ? 'Crear administrador' : 'Iniciar sesión';
    $('authTabs').classList.toggle('hidden', mode === 'setup');
    $('loginTab').classList.toggle('selected', mode === 'login');
    $('registerTab').classList.toggle('selected', mode === 'register');
    $('authError').textContent = '';
}
function openModal(mode='login') { setAuthMode(mode); showDialog('authModal'); }
function closeModal() { hideDialog('authModal'); }
async function handleLogin(event) {
    event.preventDefault();
    $('authSubmit').disabled = true; $('authError').textContent = '';
    try {
        const data = {email:$('authEmail').value, password:$('authPassword').value};
        if (authMode === 'register') Object.assign(data,{nombre:$('username').value,telefono:$('phone').value,saga_id:Number($('preferenciaSaga').value)});
        await api(authMode === 'register' ? '/api/registro' : authMode === 'setup' ? '/api/configurar-admin' : '/api/login','POST',data);
        $('authPassword').value = ''; closeModal();
        await refreshShop();
        if (usuarioActual.rol === 'admin') window.location.href = '/admin';
        else { notice('Sesión iniciada. Ya puedes confirmar tu pedido.'); if (cart.length) openCart(); }
    } catch (error) { $('authError').textContent = error.message; }
    finally { $('authSubmit').disabled = false; }
}
async function handleLogout() {
    try { await api('/api/logout','POST',{}); cart=[]; persistCart(); await refreshShop(); notice('Sesión cerrada.'); }
    catch(error) { notice(error.message,true); }
}
function addToCart(id) {
    const product = productos.find(p => p.id === id), entry = cart.find(p => p.producto_id === id);
    if (!product || (entry?.cantidad || 0) >= Math.min(product.stock,99)) return notice('No puedes añadir más unidades de este producto.',true);
    if (entry) entry.cantidad++; else cart.push({producto_id:id,cantidad:1});
    persistCart(); notice('Producto añadido al carrito.');
}
function renderCart() {
    let total=0;
    $('cartItems').innerHTML = cart.map(item => {
        const p=productos.find(p => p.id === item.producto_id);
        const subtotal=p ? p.precio*item.cantidad : 0; total+=subtotal;
        return `<div class="cart-line"><div><strong>${esc(p?.nombre || 'Producto no disponible')}</strong><p class="help">${p ? money(p.precio)+' por unidad' : 'Quita este producto para continuar.'}</p></div>
            <div class="row wrap"><label class="quantity-label">Cantidad<input class="quantity" aria-label="Cantidad de ${esc(p?.nombre || 'producto')}" type="number" min="1" max="${Math.min(p?.stock || 99,99)}" required value="${item.cantidad}" data-quantity="${item.producto_id}"></label><strong data-subtotal="${item.producto_id}">${money(subtotal)}</strong><button class="text-button" data-remove="${item.producto_id}" aria-label="Quitar ${esc(p?.nombre || 'producto')}">Quitar</button></div></div>`;
    }).join('') || '<p class="empty">Tu carrito está vacío. Añade productos del catálogo.</p>';
    updateCartTotal();
    $('checkoutBtn').disabled = !cart.length || usuarioActual?.rol === 'admin';
    $('checkoutBtn').textContent = usuarioActual?.rol === 'cliente' ? 'Confirmar pedido' : 'Iniciar sesión para continuar';
    $('checkoutHint').textContent=usuarioActual?.rol === 'admin' ? 'Para comprar, cierra la sesión de administrador e ingresa con una cuenta de cliente.' : usuarioActual ? `El pedido se registrará a nombre de ${usuarioActual.nombre}, ${usuarioActual.email}. Quedará pendiente de pago.` : 'Puedes crear una cuenta al continuar. El pedido quedará pendiente de pago.';
    $('cartError').textContent='';
}
function openCart() { renderCart(); showDialog('cartModal'); }
async function checkout() {
    if ([...$('cartItems').querySelectorAll('input')].some(input => !input.checkValidity())) { $('cartError').textContent='Revisa las cantidades antes de continuar.'; return; }
    if (!usuarioActual) { hideDialog('cartModal'); return openModal('register'); }
    $('checkoutBtn').disabled=true; $('cartError').textContent='';
    try {
        if (!orderKey) orderKey=crypto.randomUUID();
        persistCart(false);
        const result=await api('/api/pedidos','POST',{clave:orderKey,items:cart,codigo:appliedCoupon});
        appliedCoupon=''; $('couponCode').value=''; $('couponStatus').textContent='';
        cart=[]; persistCart();
        $('receiptContent').innerHTML=orderMarkup(result);
        showDialog('receiptModal');
        try { await refreshShop(); } catch (_) { notice('Pedido guardado. No se pudo actualizar el catálogo; recarga la página.',true); }
    } catch (error) { $('cartError').textContent=error.message; }
    finally { $('checkoutBtn').disabled=false; }
}
async function openOrders() {
    $('ordersContent').textContent='Cargando tus pedidos…'; showDialog('ordersModal');
    try { const orders=await api('/api/pedidos'); $('ordersContent').innerHTML=orders.map(o => orderMarkup(o)).join('') || '<p class="empty">Todavía no tienes pedidos.</p>'; }
    catch(error) { $('ordersContent').textContent=error.message; }
}
if ($('catalogGrid')) {
    document.addEventListener('DOMContentLoaded', async () => {
        $('authBtn').onclick=() => usuarioActual ? handleLogout() : openModal();
        $('cartBtn').onclick=openCart; $('ordersBtn').onclick=openOrders; $('checkoutBtn').onclick=checkout;
        $('adminLink').onclick=event => { if (configureAdmin) { event.preventDefault(); openModal('setup'); } };
        $('loginTab').onclick=() => setAuthMode('login'); $('registerTab').onclick=() => setAuthMode('register');
        $('loginForm').onsubmit=handleLogin;
        $('catalogGrid').addEventListener('click',event => { const button=event.target.closest('[data-add]'); if(button) addToCart(Number(button.dataset.add)); });
        $('cartItems').addEventListener('click',event => { const button=event.target.closest('[data-remove]'); if(button) {cart=cart.filter(x=>x.producto_id!==Number(button.dataset.remove));persistCart();renderCart();} });
        function updateQuantity(event) {
            if (!event.target.matches('[data-quantity]')) return;
            const input=event.target, id=Number(input.dataset.quantity), quantity=Number(input.value), product=productos.find(p=>p.id===id);
            if (!Number.isInteger(quantity) || quantity<1 || quantity>Math.min(product?.stock || 0,99)) { $('cartError').textContent='Revisa la cantidad y el stock disponible.';$('checkoutBtn').disabled=true;return; }
            cart.find(x=>x.producto_id===id).cantidad=quantity;persistCart();
            $('cartItems').querySelector(`[data-subtotal="${id}"]`).textContent=money(product.precio*quantity);
            updateCartTotal();
            const invalid=[...$('cartItems').querySelectorAll('input')].some(el=>!el.checkValidity());
            $('checkoutBtn').disabled=invalid||usuarioActual?.rol==='admin';$('cartError').textContent=invalid?'Revisa las cantidades.':'';
        }
        $('cartItems').addEventListener('input',updateQuantity);
        $('cartItems').addEventListener('change',updateQuantity);
        try { await refreshShop(); }
        catch(error) { $('catalogGrid').textContent=error.message; notice(error.message,true); }
    });
}

function updateCartTotal() {
    const subtotal=cart.reduce((sum,item)=>sum+(productos.find(p=>p.id===item.producto_id)?.precio||0)*item.cantidad,0);
    $('cartTotal').textContent=money(subtotal-(appliedCoupon?Math.round(subtotal*20/100):0));
}
if ($('newsletterForm')) {
    $('newsletterForm').onsubmit=async event=>{
        event.preventDefault();
        const button=event.target.querySelector('button'); button.disabled=true;
        $('newsletterStatus').textContent='Enviando tu descuento…';
        try {
            const result=await api('/api/boletin','POST',{email:$('newsletterEmail').value,consentimiento:$('newsletterConsent').checked});
            $('newsletterStatus').textContent=result.mensaje;
        } catch(error) { $('newsletterStatus').textContent=error.message; }
        finally { button.disabled=false; }
    };
    $('couponCode').oninput=()=>{appliedCoupon='';orderKey=null;$('couponStatus').textContent='';updateCartTotal();};
    $('applyCoupon').onclick=async()=>{
        const code=$('couponCode').value.trim().toUpperCase();
        $('applyCoupon').disabled=true;
        try {
            await api('/api/cupon','POST',{codigo:code});
            if ($('couponCode').value.trim().toUpperCase()!==code) return;
            appliedCoupon=code;orderKey=null;
            $('couponStatus').textContent='20% aplicado. Se verificará al confirmar el pedido.';
        } catch(error) {appliedCoupon='';$('couponStatus').textContent=error.message;}
        finally {updateCartTotal();$('applyCoupon').disabled=false;}
    };
}

document.addEventListener('error',event=>{const img=event.target;if(img.matches?.('#catalogGrid .product-media img')){const placeholder=document.createElement('span');placeholder.textContent='Imagen no disponible';img.replaceWith(placeholder);}},true);
