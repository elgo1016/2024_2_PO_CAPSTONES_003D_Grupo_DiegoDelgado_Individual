let productImageChange;
let imageJob=0, imageBusy=false;
'use strict';
let adminProducts=[], adminEvents=[], adminInstagram=[], adminSagas=[], cancelId=null;
async function loadOrders() {
    const orders=await api('/api/admin/pedidos');
    $('adminOrders').innerHTML=orders.map(o=>orderMarkup(o,true)).join('') || '<p class="empty">No hay pedidos registrados.</p>';
    $('orderStats').innerHTML=`<div class="stat"><strong>${orders.length}</strong><span>Pedidos registrados</span></div><div class="stat"><strong>${orders.filter(o=>o.estado==='pendiente_pago').length}</strong><span>Pendientes de pago</span></div><div class="stat"><strong>${orders.filter(o=>o.referencia_demo).length}</strong><span>Registros de prueba A, B y C</span></div>`;
}
async function loadProducts() {
    adminProducts=await api('/api/admin/productos');
    $('productList').innerHTML='<table><thead><tr><th>Producto</th><th>Precio</th><th>Stock</th><th>Acción</th></tr></thead><tbody>'+adminProducts.map(p=>`<tr><td><strong>${esc(p.nombre)}</strong><small>${esc(adminSagas.find(s=>s.id===p.saga_id)?.nombre)} · ${p.activo?'Visible':'Oculto'}</small></td><td>${money(p.precio)}</td><td>${p.stock}</td><td><button class="ui-button secondary small" data-edit-product="${p.id}">Editar producto ${p.id}</button></td></tr>`).join('')+'</tbody></table>';
}
async function loadClients() {
    const clients=await api('/api/admin/clientes');
    $('clientList').innerHTML='<table><thead><tr><th>ID</th><th>Nombre</th><th>Correo</th><th>Teléfono</th><th>Saga favorita</th></tr></thead><tbody>'+clients.map(c=>`<tr><td>${c.id}</td><td>${esc(c.nombre)}</td><td>${esc(c.email)}</td><td>${esc(c.telefono||'—')}</td><td>${esc(c.saga||'—')}</td></tr>`).join('')+'</tbody></table>';
}
async function loadEvents() {
    adminEvents=await api('/api/admin/eventos');
    $('eventList').innerHTML='<table><thead><tr><th>Evento</th><th>Fecha</th><th>Acción</th></tr></thead><tbody>'+adminEvents.map(e=>`<tr><td><strong>${esc(e.nombre)}</strong><small>${esc(e.ubicacion)} · ${e.activo?'Publicado':'Oculto'}</small></td><td>${esc(e.fecha)}</td><td><button class="ui-button secondary small" data-edit-event="${e.id}">Editar evento ${e.id}</button></td></tr>`).join('')+'</tbody></table>';
}
async function loadInstagram() {
    adminInstagram=await api('/api/admin/instagram');
    $('instagramList').innerHTML='<table><thead><tr><th>Publicación</th><th>Estado</th><th>Acción</th></tr></thead><tbody>'+adminInstagram.map(p=>`<tr><td><strong>${esc(p.titulo)}</strong><small>${esc(p.enlace)}</small></td><td>${p.activo?'Publicado':'Oculto'}</td><td><button class="ui-button secondary small" data-edit-instagram="${p.id}">Editar publicación ${p.id}</button></td></tr>`).join('')+'</tbody></table>';
}
function resetProduct() { setProductImage(''); $('productForm').reset();$('productId').value='';$('productFormTitle').textContent='Nuevo producto';$('productError').textContent=''; }
function resetEvent() { $('eventForm').reset();$('eventId').value='';$('eventFormTitle').textContent='Nuevo evento';$('eventError').textContent=''; }
function resetInstagram() { $('instagramForm').reset();$('instagramId').value='';$('instagramFormTitle').textContent='Nueva publicación';$('instagramError').textContent=''; }
document.addEventListener('DOMContentLoaded',async()=>{
    try {
        const init=await api('/api/inicio');adminSagas=init.sagas;
        if(init.imagenes_version!==1){$('saveProduct').disabled=true;throw new Error('Esta pestaña está conectada al servidor antiguo, que no admite imágenes. Abre INICIAR_CON_GMAIL.bat y utiliza la nueva pestaña que se abre automáticamente.');}
        if(init.usuario?.rol!=='admin'){
            $('adminGate').classList.remove('hidden');$('gateMessage').textContent=init.configurar_admin?'Primero crea el administrador usando «Configurar administración» al pie de la tienda.':'Inicia sesión con tu cuenta de administrador desde la tienda para acceder.';return;
        }
        $('adminApp').classList.remove('hidden');$('adminLogout').classList.remove('hidden');
        $('businessInfo').innerHTML=`<h3>${esc(init.negocio.nombre)}</h3><p>${esc(init.negocio.descripcion)}</p><p class="help">Identificador: ${init.negocio.id}</p>`;
        $('productSaga').innerHTML=adminSagas.map(s=>`<option value="${s.id}">${esc(s.nombre)}</option>`).join('');
        await Promise.all([loadOrders(),loadProducts(),loadClients(),loadEvents(),loadInstagram()]);
    } catch(error){notice(error.message,true);$('adminGate').classList.remove('hidden');$('gateMessage').textContent=error.message;}
    finally{$('adminLoading').classList.add('hidden');}
});
document.querySelector('.admin-nav').addEventListener('click',async event=>{
    const button=event.target.closest('[data-panel]');if(!button)return;
    document.querySelectorAll('.admin-panel').forEach(p=>p.classList.toggle('hidden',p.id!=='panel-'+button.dataset.panel));
    document.querySelectorAll('[data-panel]').forEach(b=>b.classList.toggle('active',b===button));
    try {if(button.dataset.panel==='pedidos')await loadOrders();if(button.dataset.panel==='productos')await loadProducts();if(button.dataset.panel==='eventos')await loadEvents();if(button.dataset.panel==='instagram')await loadInstagram();if(button.dataset.panel==='clientes')await loadClients();}catch(error){notice(error.message,true);}
});
$('adminLogout').onclick=async()=>{try{await api('/api/logout','POST',{});window.location.href='/';}catch(error){notice(error.message,true);}};
$('reloadOrders').onclick=async()=>{try{await loadOrders();notice('Lista de pedidos actualizada.');}catch(error){notice(error.message,true);}};
$('newProduct').onclick=resetProduct;$('newEvent').onclick=resetEvent;$('newInstagram').onclick=resetInstagram;
$('productList').onclick=event=>{
    const button=event.target.closest('[data-edit-product]');if(!button)return;
    const p=adminProducts.find(p=>p.id===Number(button.dataset.editProduct));
    setProductImage(p.imagen || '');
    $('productId').value=p.id;$('productName').value=p.nombre;$('productSaga').value=p.saga_id;$('productPrice').value=p.precio;$('productStock').value=p.stock;$('productActive').value=p.activo;$('productFormTitle').textContent='Editar producto '+p.id;$('productError').textContent='';$('productName').focus();
};
$('eventList').onclick=event=>{
    const button=event.target.closest('[data-edit-event]');if(!button)return;
    const e=adminEvents.find(e=>e.id===Number(button.dataset.editEvent));
    $('eventId').value=e.id;$('eventName').value=e.nombre;$('eventDate').value=e.fecha;$('eventPlace').value=e.ubicacion;$('eventDetail').value=e.detalle;$('eventActive').value=e.activo;$('eventFormTitle').textContent='Editar evento '+e.id;$('eventError').textContent='';$('eventName').focus();
};
$('instagramList').onclick=event=>{
    const button=event.target.closest('[data-edit-instagram]');if(!button)return;
    const p=adminInstagram.find(p=>p.id===Number(button.dataset.editInstagram));
    $('instagramId').value=p.id;$('instagramTitle').value=p.titulo;$('instagramLink').value=p.enlace;$('instagramDescription').value=p.descripcion;$('instagramActive').value=p.activo;$('instagramFormTitle').textContent='Editar publicación '+p.id;$('instagramError').textContent='';$('instagramTitle').focus();
};
$('productForm').onsubmit=async event=>{
    event.preventDefault();if(imageBusy)return;$('saveProduct').disabled=true;$('productError').textContent='';
    try{const id=$('productId').value;await api('/api/admin/productos'+(id?'/'+id:''),id?'PUT':'POST',{nombre:$('productName').value,saga_id:Number($('productSaga').value),precio:Number($('productPrice').value),stock:Number($('productStock').value),activo:Number($('productActive').value),...(productImageChange!==undefined?{imagen:productImageChange}:{})});resetProduct();await loadProducts();notice('Producto guardado.');}
    catch(error){$('productError').textContent=error.message;}finally{$('saveProduct').disabled=false;}
};
$('eventForm').onsubmit=async event=>{
    event.preventDefault();$('saveEvent').disabled=true;$('eventError').textContent='';
    try{const id=$('eventId').value;await api('/api/admin/eventos'+(id?'/'+id:''),id?'PUT':'POST',{nombre:$('eventName').value,fecha:$('eventDate').value,ubicacion:$('eventPlace').value,detalle:$('eventDetail').value,activo:Number($('eventActive').value)});resetEvent();await loadEvents();notice('Evento guardado.');}
    catch(error){$('eventError').textContent=error.message;}finally{$('saveEvent').disabled=false;}
};
$('instagramForm').onsubmit=async event=>{
    event.preventDefault();$('saveInstagram').disabled=true;$('instagramError').textContent='';
    try{const id=$('instagramId').value;await api('/api/admin/instagram'+(id?'/'+id:''),id?'PUT':'POST',{titulo:$('instagramTitle').value,enlace:$('instagramLink').value,descripcion:$('instagramDescription').value,activo:Number($('instagramActive').value)});resetInstagram();await loadInstagram();notice('Publicación de Instagram guardada.');}
    catch(error){$('instagramError').textContent=error.message;}finally{$('saveInstagram').disabled=false;}
};
$('adminOrders').onclick=event=>{const button=event.target.closest('[data-cancel-order]');if(!button)return;cancelId=Number(button.dataset.cancelOrder);$('cancelDescription').textContent=`Se cancelará el pedido PD-${String(cancelId).padStart(6,'0')}.`;$('cancelError').textContent='';showDialog('cancelModal');};
$('confirmCancel').onclick=async()=>{
    $('confirmCancel').disabled=true;
    try{await api(`/api/admin/pedidos/${cancelId}/cancelar`,'POST',{});hideDialog('cancelModal');await loadOrders();notice('Pedido cancelado y stock restituido.');}
    catch(error){$('cancelError').textContent=error.message;}finally{$('confirmCancel').disabled=false;}
};

function previewProductImage(source) {
    const image=$('productImagePreview');
    image.hidden=!source; $('productImageEmpty').hidden=Boolean(source);
    if(source) image.src=source; else image.removeAttribute('src');
    $('removeProductImage').disabled=!source;
}
function setProductImage(source) {
    imageJob++; imageBusy=false; productImageChange=undefined;
    $('productImage').value=''; $('productImageStatus').textContent=''; $('saveProduct').disabled=false;
    previewProductImage(source);
}
$('productImagePreview').onerror=()=>{
    $('productImagePreview').hidden=true;$('productImageEmpty').hidden=false;
    $('productImageEmpty').textContent='No se pudo cargar la imagen';
};
$('removeProductImage').onclick=()=>{
    setProductImage('');productImageChange='';$('productImageEmpty').textContent='Sin imagen';
};
$('productImage').onchange=async()=>{
    const file=$('productImage').files[0]; if(!file)return;
    const job=++imageJob;imageBusy=true;$('saveProduct').disabled=true;$('productError').textContent='';
    $('productImageStatus').textContent='Preparando imagen…';
    let url;
    try {
        if(!['image/jpeg','image/png','image/webp'].includes(file.type))throw new Error('Elige una imagen JPG, PNG o WebP.');
        if(file.size>30*1024*1024)throw new Error('La imagen supera 30 MB. Elige una más pequeña.');
        url=URL.createObjectURL(file);
        const image=new Image();
        await new Promise((resolve,reject)=>{image.onload=resolve;image.onerror=()=>reject(new Error('No se pudo abrir esta imagen. Elige otro archivo.'));image.src=url;});
        if(image.naturalWidth*image.naturalHeight>40000000)throw new Error('La imagen supera 40 megapíxeles. Reduce su resolución.');
        let scale=Math.min(1,1600/image.naturalWidth,1600/image.naturalHeight), encoded;
        const canvas=document.createElement('canvas');
        for(let attempt=0;attempt<8;attempt++){
            canvas.width=Math.max(1,Math.round(image.naturalWidth*scale));canvas.height=Math.max(1,Math.round(image.naturalHeight*scale));
            canvas.getContext('2d').drawImage(image,0,0,canvas.width,canvas.height);
            encoded=canvas.toDataURL('image/png');
            if(encoded.length<=2796200)break;
            scale*=0.75;
        }
        if(!encoded.startsWith('data:image/png;base64,') || encoded.length>2796200)throw new Error('No se pudo preparar la imagen. Elige una más pequeña.');
        if(job!==imageJob)return;
        productImageChange=encoded;previewProductImage(encoded);
        $('productImageStatus').textContent='Imagen lista. Pulsa Guardar producto para aplicar el cambio.';
    }catch(error){if(job===imageJob){$('productError').textContent=error.message;$('productImageStatus').textContent='';$('productImage').value='';}}
    finally{if(url)URL.revokeObjectURL(url);if(job===imageJob){imageBusy=false;$('saveProduct').disabled=false;}}
};
