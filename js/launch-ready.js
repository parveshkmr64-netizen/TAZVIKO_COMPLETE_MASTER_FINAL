(function(){
 const api=async(path,opt={})=>{const token=localStorage.getItem('tazviko_token')||'';const controller=new AbortController();const timer=setTimeout(()=>controller.abort(),15000);try{const r=await fetch('/api/v1'+path,{headers:{'Content-Type':'application/json',...(token?{'Authorization':'Bearer '+token}:{})},signal:controller.signal,...opt});const j=await r.json().catch(()=>({}));if(!r.ok)throw new Error(j.error||('HTTP '+r.status));return j}catch(e){if(e.name==='AbortError')throw new Error('server_timeout');if(e instanceof TypeError)throw new Error('server_unavailable');throw e}finally{clearTimeout(timer)}};
 let gatewayConfig={online_payment_enabled:false,razorpay_key_id:''};
 async function loadConfig(){try{gatewayConfig=await api('/config');}catch(e){}}
 function replaceAccount(){const m=document.getElementById('accountModal');if(!m)return;m.innerHTML=`<div class="modal-box wide"><h3>TAZVIKO Account</h3><div id="authLoggedOut" class="split"><div class="panel"><h4>Login</h4><input class="field" id="loginMobile" placeholder="Mobile number"><input class="field" id="loginPin" type="password" placeholder="4+ digit PIN"><button class="btn btn-primary" onclick="tazLogin()">Login</button></div><div class="panel"><h4>Create account</h4><input class="field" id="regName" placeholder="Name"><input class="field" id="regMobile" placeholder="Mobile number"><input class="field" id="regEmail" placeholder="Email (optional)"><input class="field" id="regPin" type="password" placeholder="Create 4+ digit PIN"><button class="btn btn-primary" onclick="tazRegister()">Create Account</button></div></div><div id="authLoggedIn" class="panel" style="display:none"><h4 id="authName">My Account</h4><div id="authMeta" class="muted"></div><div class="modal-actions" style="margin-top:14px"><button class="btn btn-outline" onclick="tazLogout()">Logout</button></div></div></div>`;refreshAccount();}
 async function refreshAccount(){const out=document.getElementById('authLoggedOut'),inn=document.getElementById('authLoggedIn');if(!out||!inn)return;const token=localStorage.getItem('tazviko_token');if(!token){out.style.display='grid';inn.style.display='none';return}try{const x=await api('/auth/me');out.style.display='none';inn.style.display='block';document.getElementById('authName').textContent='Hello, '+x.user.name;document.getElementById('authMeta').textContent=x.user.mobile+(x.user.email?' • '+x.user.email:'');}catch(e){localStorage.removeItem('tazviko_token');out.style.display='grid';inn.style.display='none'}}
 window.tazRegister=async()=>{try{const x=await api('/auth/register',{method:'POST',body:JSON.stringify({name:regName.value.trim(),mobile:regMobile.value.trim(),email:regEmail.value.trim(),pin:regPin.value})});localStorage.setItem('tazviko_token',x.token);notify('Account created');refreshAccount();}catch(e){notify('Account: '+e.message)}};
 window.tazLogin=async()=>{try{const x=await api('/auth/login',{method:'POST',body:JSON.stringify({mobile:loginMobile.value.trim(),pin:loginPin.value})});localStorage.setItem('tazviko_token',x.token);notify('Login successful');refreshAccount();}catch(e){notify('Login failed')}};
 window.tazLogout=()=>{localStorage.removeItem('tazviko_token');notify('Logged out');refreshAccount()};
 function injectCustomerFields(){prefillUser();const address=document.getElementById('pilotAddress');if(address&&!address.value){try{address.value=localStorage.getItem('tazviko_location')||''}catch(e){}}}
 async function prefillUser(){if(!localStorage.getItem('tazviko_token'))return;try{const x=await api('/auth/me');if(window.pilotName)pilotName.value=x.user.name||'';if(window.pilotMobile)pilotMobile.value=x.user.mobile||'';}catch(e){}}
 window.openCart=(function(old){return function(){injectCustomerFields();prefillUser();old();};})(window.openCart);
 function loadRazorpay(){return new Promise((res,rej)=>{if(window.Razorpay)return res();const s=document.createElement('script');s.src='https://checkout.razorpay.com/v1/checkout.js';s.onload=res;s.onerror=rej;document.head.appendChild(s)})}
 function clearAfterOrder(code){localStorage.setItem('tazviko_last_order',code);cart=[];discount=0;activeCoupon='';syncCart();closeModal('cartModal');const tr=document.querySelector('#trackingModal h3');if(tr)tr.textContent='Order '+code+' • Live Tracking';openModal('trackingModal')}
 window.placeDemoOrder=async function(){
   if(!cart.length){notify(t('emptyCart'));return}
   const name=(document.getElementById('pilotName')?.value||'').trim();
   const mobile=(document.getElementById('pilotMobile')?.value||'').trim();
   const address=(document.getElementById('pilotAddress')?.value||'').trim();
   const status=document.getElementById('checkoutStatus');
   const showStatus=(message,isError=false)=>{if(!status)return;status.style.display='block';status.style.background=isError?'#ffe9e5':'#e9f8f1';status.style.color=isError?'#a12a16':'#08794e';status.textContent=message};
   if(!name){document.getElementById('pilotName')?.focus();showStatus('Customer name fill karein.',true);return}
   if(!/^\+?[0-9][0-9\s-]{7,14}$/.test(mobile)){document.getElementById('pilotMobile')?.focus();showStatus('Sahi mobile number fill karein.',true);return}
   if(address.length<8){document.getElementById('pilotAddress')?.focus();showStatus('Full delivery address fill karein.',true);return}
   const method=(payMethod==='COD'?'COD':'RAZORPAY');
   if(method==='RAZORPAY'&&!gatewayConfig.online_payment_enabled){notify('Online payment is not active yet. Please choose COD.');return}
   const btn=document.getElementById('placeOrderBtn'); const oldText=btn?btn.textContent:''; if(btn){btn.disabled=true;btn.textContent='Placing COD order...'}showStatus('Order server par save ho raha hai…');
   try{
     const secureItems=cart.map(x=>({name:x.name,merchant:x.merchant,qty:x.qty}));
     const out=await api('/orders',{method:'POST',body:JSON.stringify({customer_name:name,mobile,address,items:secureItems,payment_method:method,coupon:activeCoupon})});
     if(method==='COD'){showStatus('COD order '+out.order_code+' successfully placed.');clearAfterOrder(out.order_code);notify('COD order '+out.order_code+' placed successfully');return}
     const p=await api('/payments/create',{method:'POST',body:JSON.stringify({order_code:out.order_code})});await loadRazorpay();
     const rz=new Razorpay({key:p.key_id,amount:p.amount,currency:'INR',name:'TAZVIKO',description:'Order '+out.order_code,order_id:p.razorpay_order_id,prefill:{name,contact:mobile},handler:async function(resp){try{await api('/payments/verify',{method:'POST',body:JSON.stringify({order_code:out.order_code,...resp})});clearAfterOrder(out.order_code);notify('Payment successful • '+out.order_code);}catch(e){notify('Payment verification failed')}}});rz.open();
   }catch(e){const message=e.message==='server_unavailable'?'Server connect nahi ho raha. Render wali live URL kholen; GitHub preview se COD save nahi hoga.':e.message==='server_timeout'?'Server start hone mein time lag raha hai. 20 seconds baad dobara try karein.':'Order failed: '+e.message;showStatus(message,true);notify(message)}finally{if(btn){btn.disabled=false;btn.textContent=oldText||'Place COD Order'}}
 };
 window.submitPartner=async function(){const n=bizName.value.trim(),city=bizCity.value.trim(),type=bizType.value;if(!n){notify(t('businessName'));return}if(!partnerAgree.checked){notify('Please accept partner terms');return}const payload={business_name:n,business_type:type,city,owner_name:(window.ownerName&&ownerName.value)||'',address:(window.bizAddress&&bizAddress.value)||'',phone:'',bank_ref:'',catalog:document.querySelector('#partnerModal textarea:last-of-type')?.value||''};try{await api('/partners/applications',{method:'POST',body:JSON.stringify(payload)});closeModal('partnerModal');notify('Restaurant/shop sent for admin approval');}catch(e){notify('Application failed: '+e.message)}};
 async function refreshTracking(){const code=localStorage.getItem('tazviko_last_order');if(!code)return;try{const x=await api('/orders/'+encodeURIComponent(code)+'/tracking');const tr=document.querySelector('#trackingModal h3');if(tr)tr.textContent='Order '+x.order_code+' • '+x.status.replaceAll('_',' ');const b=document.getElementById('trackingBody');if(b)b.innerHTML='<b>Status:</b> '+x.status.replaceAll('_',' ')+'<br><b>Payment:</b> '+x.payment_method+' / '+x.payment_status+'<br><b>Total:</b> ₹'+x.total+'<br><span class="muted">Last updated from the TAZVIKO server.</span>';}catch(e){}}
 async function refreshQuoteUI(){
   if(!cart.length)return updateCartUI();
   try{
     const secureItems=cart.map(x=>({name:x.name,merchant:x.merchant,qty:x.qty}));
     const q=await api('/quote',{method:'POST',body:JSON.stringify({items:secureItems,coupon:activeCoupon})});
     discount=q.discount||0; deliveryFeeAmt=q.delivery_fee||0;
     document.getElementById('subTotal').textContent='₹'+q.subtotal;
     document.getElementById('discount').textContent='-₹'+q.discount;
     document.getElementById('delivery').textContent='₹'+q.delivery_fee;
     document.getElementById('platform').textContent='₹'+q.platform_fee;
     document.getElementById('tax').textContent='₹'+q.tax;
     document.getElementById('grandTotal').textContent='₹'+q.total;
   }catch(e){}
 }
 window.applyCoupon=async function(){
   const code=document.getElementById('couponInput').value.trim().toUpperCase();
   if(!cart.length){notify(t('emptyCart'));return}
   try{const secureItems=cart.map(x=>({name:x.name,merchant:x.merchant,qty:x.qty}));const q=await api('/quote',{method:'POST',body:JSON.stringify({items:secureItems,coupon:code})});if(!q.coupon){activeCoupon='';notify('Coupon not applicable');}else{activeCoupon=q.coupon;notify('Coupon '+q.coupon+' applied');}await refreshQuoteUI();}catch(e){notify('Coupon: '+e.message)}
 };
 window.submitSupportTicket=async function(){
   const message=(document.getElementById('supportMessage')?.value||'').trim(); if(!message){notify('Please enter your support message');return}
   try{const x=await api('/support/tickets',{method:'POST',body:JSON.stringify({category:document.getElementById('supportCategory').value,mobile:document.getElementById('supportMobile').value.trim(),message})});document.getElementById('supportMessage').value='';closeModal('supportModal');notify('Support ticket #'+x.ticket_id+' created');}catch(e){notify('Support: '+e.message)}
 };
 window.submitDeliveryPartner=async function(){
   const full_name=deliveryName.value.trim(),mobile=deliveryMobile.value.trim(); if(!full_name||!mobile){notify('Name and mobile are required');return}
   try{await api('/delivery/applications',{method:'POST',body:JSON.stringify({full_name,mobile,vehicle_type:deliveryVehicleType.value,vehicle_number:deliveryVehicleNumber.value.trim(),identity_ref:deliveryIdentity.value.trim(),payout_ref:deliveryPayout.value.trim()})});closeModal('deliveryPartnerModal');notify('Delivery partner application submitted for review');}catch(e){notify('Application: '+e.message)}
 };
 async function loadMyOrders(){const box=document.getElementById('realOrdersList');if(!box)return;if(!localStorage.getItem('tazviko_token')){box.innerHTML='<div class="muted">Login to view your orders.</div>';return}try{const x=await api('/orders/mine');box.innerHTML=x.orders.length?x.orders.map(o=>`<div class="list-item"><div><b>${o.order_code} • ${o.merchant||'TAZVIKO'}</b><div class="muted">₹${o.total} • ${o.payment_status} • ${o.status}</div></div><button class="btn btn-primary" onclick="trackSpecificOrder('${o.order_code}')">Track</button></div>`).join(''):'<div class="muted">No orders yet.</div>';}catch(e){box.innerHTML='<div class="muted">Please login again to view orders.</div>'}}
 window.trackSpecificOrder=async function(code){localStorage.setItem('tazviko_last_order',code);await refreshTracking();openModal('trackingModal')};
 const originalOpenModal=window.openModal; window.openModal=function(id){if(id==='ordersModal')loadMyOrders();return originalOpenModal(id)};
 async function initLaunch(){await loadConfig();replaceAccount();injectCustomerFields();document.querySelectorAll('[data-online-pay]').forEach(el=>{if(!gatewayConfig.online_payment_enabled){el.style.opacity='.45';el.title='Online payment will be enabled after payment KYC/setup';}});payMethod='COD';const cod=document.getElementById('codPayOption');if(cod)selectPay(cod,'COD');const orderButton=document.getElementById('placeOrderBtn');if(orderButton){orderButton.onclick=null;orderButton.addEventListener('click',event=>{event.preventDefault();window.placeDemoOrder()});}setInterval(refreshTracking,8000);refreshTracking();const badge=document.createElement('div');badge.style.cssText='position:fixed;bottom:16px;left:16px;z-index:80;background:#172033;color:#fff;padding:9px 12px;border-radius:999px;font:700 12px system-ui;box-shadow:0 8px 24px #0002';badge.textContent=gatewayConfig.online_payment_enabled?'● TAZVIKO Live • COD + Online':'● TAZVIKO Live • COD';document.body.appendChild(badge);}
 initLaunch();
})();
