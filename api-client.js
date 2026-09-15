window.TazvikoAPI={
  async request(path,options={}){
    const base=(window.TAZVIKO_CONFIG&&TAZVIKO_CONFIG.apiBaseUrl)||'/api/v1';
    const token=localStorage.getItem('tazviko_token')||'';
    const res=await fetch(base+path,{headers:{'Content-Type':'application/json',...(token?{'Authorization':'Bearer '+token}:{}),...(options.headers||{})},...options});
    const data=await res.json().catch(()=>({}));
    if(!res.ok) throw new Error(data.error||('API '+res.status));
    return data;
  },
  register:(payload)=>TazvikoAPI.request('/auth/register',{method:'POST',body:JSON.stringify(payload)}),
  login:(payload)=>TazvikoAPI.request('/auth/login',{method:'POST',body:JSON.stringify(payload)}),
  me:()=>TazvikoAPI.request('/auth/me'),
  catalog:()=>TazvikoAPI.request('/catalog'),
  quote:(payload)=>TazvikoAPI.request('/quote',{method:'POST',body:JSON.stringify(payload)}),
  createOrder:(payload)=>TazvikoAPI.request('/orders',{method:'POST',body:JSON.stringify(payload)}),
  myOrders:()=>TazvikoAPI.request('/orders/mine'),
  createPayment:(payload)=>TazvikoAPI.request('/payments/create',{method:'POST',body:JSON.stringify(payload)}),
  verifyPayment:(payload)=>TazvikoAPI.request('/payments/verify',{method:'POST',body:JSON.stringify(payload)}),
  partnerApply:(payload)=>TazvikoAPI.request('/partners/applications',{method:'POST',body:JSON.stringify(payload)}),
  deliveryApply:(payload)=>TazvikoAPI.request('/delivery/applications',{method:'POST',body:JSON.stringify(payload)}),
  supportTicket:(payload)=>TazvikoAPI.request('/support/tickets',{method:'POST',body:JSON.stringify(payload)}),
  trackOrder:(id)=>TazvikoAPI.request('/orders/'+encodeURIComponent(id)+'/tracking'),
  nearby:(lat,lng,category='all',radius=4000)=>TazvikoAPI.request('/places/nearby?lat='+encodeURIComponent(lat)+'&lng='+encodeURIComponent(lng)+'&category='+encodeURIComponent(category)+'&radius='+encodeURIComponent(radius))
};
