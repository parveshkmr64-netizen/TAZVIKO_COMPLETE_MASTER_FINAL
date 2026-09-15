(function(){
  const api=(path,opt={})=>fetch('/api/v1'+path,{headers:{'Content-Type':'application/json'},...opt}).then(async r=>{const j=await r.json().catch(()=>({}));if(!r.ok)throw new Error(j.error||('HTTP '+r.status));return j});
  function injectCustomerFields(){
    const pay=document.querySelector('.payopts'); if(!pay || document.getElementById('pilotCustomer')) return;
    const box=document.createElement('div'); box.id='pilotCustomer'; box.className='panel'; box.style.margin='14px 0';
    box.innerHTML='<b>Delivery details</b><div class="row2" style="margin-top:10px"><input class="field" id="pilotName" placeholder="Customer name"><input class="field" id="pilotMobile" placeholder="Mobile number"></div><textarea class="field" id="pilotAddress" placeholder="Full delivery address" style="min-height:75px"></textarea><div class="muted">Starter mode: COD works without a payment gateway. Online payments can be enabled later by connecting Razorpay/Cashfree/PhonePe through the backend.</div>';
    pay.parentNode.insertBefore(box,pay);
  }
  window.openCart=(function(old){return function(){injectCustomerFields(); old();};})(window.openCart);
  window.placeDemoOrder=async function(){
    if(!cart.length){notify(t('emptyCart'));return}
    injectCustomerFields();
    const name=document.getElementById('pilotName').value.trim(), mobile=document.getElementById('pilotMobile').value.trim(), address=document.getElementById('pilotAddress').value.trim();
    if(!name||!mobile||!address){notify('Name, mobile and delivery address are required');return}
    if(payMethod!=='COD'){notify('Online payment gateway is not connected yet. Please use Cash on Delivery for now.');return}
    const c=calc(), merchant=cart[0].merchant||'TAZVIKO Partner';
    try{
      const out=await api('/orders',{method:'POST',body:JSON.stringify({customer_name:name,mobile,address,merchant,items:cart,subtotal:c.sub,discount:c.disc,delivery_fee:c.del,platform_fee:c.plat,tax:c.tax,total:c.total,commission:c.commission,merchant_payable:c.merchant,tazviko_earning:c.earn,payment_method:payMethod,coupon:activeCoupon})});
      localStorage.setItem('tazviko_last_order',out.order_code);
      cart=[];discount=0;activeCoupon='';syncCart();closeModal('cartModal');
      const tr=document.querySelector('#trackingModal h3'); if(tr) tr.textContent='Order '+out.order_code+' • Live Tracking';
      notify('Order '+out.order_code+' saved successfully'); openModal('trackingModal');
    }catch(e){notify('Order could not be saved: '+e.message)}
  };
  window.submitPartner=async function(){
    const n=document.getElementById('bizName').value.trim(),city=document.getElementById('bizCity').value.trim(),type=document.getElementById('bizType').value;
    if(!n){notify(t('businessName'));return} if(!document.getElementById('partnerAgree').checked){notify('Please accept partner terms');return}
    const inputs=[...document.querySelectorAll('#partnerModal input, #partnerModal textarea')];
    const payload={business_name:n,business_type:type,city,owner_name:inputs.find(x=>/owner/i.test(x.placeholder||''))?.value||'',address:inputs.find(x=>/address/i.test(x.placeholder||''))?.value||'',phone:inputs.find(x=>/phone|mobile/i.test(x.placeholder||''))?.value||'',bank_ref:inputs.find(x=>/bank/i.test(x.placeholder||''))?.value||'',catalog:document.querySelector('#partnerModal textarea')?.value||''};
    try{await api('/partners/applications',{method:'POST',body:JSON.stringify(payload)});closeModal('partnerModal');notify('Partner application saved for admin approval');}
    catch(e){notify('Application failed: '+e.message)}
  };
  async function refreshTracking(){const code=localStorage.getItem('tazviko_last_order');if(!code)return;try{const x=await api('/orders/'+encodeURIComponent(code)+'/tracking');const tr=document.querySelector('#trackingModal h3');if(tr)tr.textContent='Order '+x.order_code+' • '+x.status.replaceAll('_',' ');}catch(e){}}
  setInterval(refreshTracking,8000); refreshTracking(); injectCustomerFields();
  const badge=document.createElement('div');badge.style.cssText='position:fixed;bottom:16px;left:16px;z-index:80;background:#172033;color:#fff;padding:9px 12px;border-radius:999px;font:700 12px system-ui;box-shadow:0 8px 24px #0002';badge.textContent='● TAZVIKO Live Starter • COD';document.body.appendChild(badge);
})();
