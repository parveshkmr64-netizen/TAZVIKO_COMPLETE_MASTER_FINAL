#!/usr/bin/env python3
import os, json, sqlite3, secrets, hashlib, hmac, base64, urllib.request, urllib.error, time, threading
from datetime import datetime, timezone, timedelta
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DB_PATH = Path(os.environ.get('TAZVIKO_DB_PATH', str(ROOT / 'data' / 'tazviko.sqlite3'))).expanduser().resolve()
PORT = int(os.environ.get('PORT','8000'))
ADMIN_KEY = os.environ.get('TAZVIKO_ADMIN_KEY','change-me-now')
RAZORPAY_KEY_ID = os.environ.get('RAZORPAY_KEY_ID','').strip()
RAZORPAY_KEY_SECRET = os.environ.get('RAZORPAY_KEY_SECRET','').strip()
PUBLIC_BASE_URL = os.environ.get('PUBLIC_BASE_URL','').strip()
GOOGLE_PLACES_API_KEY = os.environ.get('GOOGLE_PLACES_API_KEY','').strip()
MAX_BODY = int(os.environ.get('TAZVIKO_MAX_BODY','1048576'))
RATE_LIMIT = int(os.environ.get('TAZVIKO_RATE_LIMIT','120'))
COMMISSION_BPS = int(os.environ.get('TAZVIKO_COMMISSION_BPS','1500'))  # 15.00%
PLATFORM_FEE = int(os.environ.get('TAZVIKO_PLATFORM_FEE','9'))
DELIVERY_FEE = int(os.environ.get('TAZVIKO_DELIVERY_FEE','29'))
TAX_BPS = int(os.environ.get('TAZVIKO_TAX_BPS','500'))  # demo 5.00%; configure for your tax treatment
_rate = {}
_rate_lock = threading.Lock()

SCHEMA = '''
CREATE TABLE IF NOT EXISTS users (
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 created_at TEXT NOT NULL,
 name TEXT NOT NULL,
 mobile TEXT UNIQUE NOT NULL,
 email TEXT,
 pin_hash TEXT NOT NULL,
 status TEXT NOT NULL DEFAULT 'ACTIVE'
);
CREATE TABLE IF NOT EXISTS sessions (
 token TEXT PRIMARY KEY,
 user_id INTEGER NOT NULL,
 created_at TEXT NOT NULL,
 expires_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS orders (
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 order_code TEXT UNIQUE NOT NULL,
 created_at TEXT NOT NULL,
 user_id INTEGER,
 customer_name TEXT NOT NULL,
 mobile TEXT NOT NULL,
 address TEXT NOT NULL,
 merchant TEXT,
 items_json TEXT NOT NULL,
 subtotal INTEGER NOT NULL,
 discount INTEGER NOT NULL DEFAULT 0,
 delivery_fee INTEGER NOT NULL DEFAULT 0,
 platform_fee INTEGER NOT NULL DEFAULT 0,
 tax INTEGER NOT NULL DEFAULT 0,
 total INTEGER NOT NULL,
 commission INTEGER NOT NULL DEFAULT 0,
 merchant_payable INTEGER NOT NULL DEFAULT 0,
 tazviko_earning INTEGER NOT NULL DEFAULT 0,
 payment_method TEXT NOT NULL DEFAULT 'COD',
 payment_status TEXT NOT NULL DEFAULT 'COD_PENDING',
 provider_order_id TEXT,
 provider_payment_id TEXT,
 status TEXT NOT NULL DEFAULT 'PLACED'
);
CREATE TABLE IF NOT EXISTS partners (
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 created_at TEXT NOT NULL,
 business_name TEXT NOT NULL,
 owner_name TEXT,
 business_type TEXT,
 city TEXT,
 address TEXT,
 phone TEXT,
 bank_ref TEXT,
 catalog TEXT,
 status TEXT NOT NULL DEFAULT 'REVIEW',
 latitude REAL,
 longitude REAL,
 google_place_id TEXT,
 source TEXT NOT NULL DEFAULT 'TAZVIKO'
);
CREATE TABLE IF NOT EXISTS merchant_sessions (
 token TEXT PRIMARY KEY,
 partner_id INTEGER NOT NULL,
 created_at TEXT NOT NULL,
 expires_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS riders (
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 created_at TEXT NOT NULL,
 full_name TEXT NOT NULL,
 mobile TEXT UNIQUE NOT NULL,
 pin_hash TEXT NOT NULL,
 status TEXT NOT NULL DEFAULT 'ACTIVE'
);
CREATE TABLE IF NOT EXISTS rider_sessions (
 token TEXT PRIMARY KEY,
 rider_id INTEGER NOT NULL,
 created_at TEXT NOT NULL,
 expires_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS products (
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 product_key TEXT UNIQUE NOT NULL,
 name TEXT NOT NULL,
 merchant TEXT NOT NULL,
 price INTEGER NOT NULL,
 active INTEGER NOT NULL DEFAULT 1
);
CREATE TABLE IF NOT EXISTS coupons (
 code TEXT PRIMARY KEY,
 discount_type TEXT NOT NULL,
 discount_value INTEGER NOT NULL,
 min_subtotal INTEGER NOT NULL DEFAULT 0,
 max_discount INTEGER NOT NULL DEFAULT 0,
 active INTEGER NOT NULL DEFAULT 1
);
CREATE TABLE IF NOT EXISTS support_tickets (
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 created_at TEXT NOT NULL,
 user_id INTEGER,
 mobile TEXT,
 category TEXT,
 message TEXT NOT NULL,
 status TEXT NOT NULL DEFAULT 'OPEN'
);
CREATE TABLE IF NOT EXISTS delivery_applications (
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 created_at TEXT NOT NULL,
 full_name TEXT NOT NULL,
 mobile TEXT NOT NULL,
 vehicle_type TEXT,
 vehicle_number TEXT,
 identity_ref TEXT,
 payout_ref TEXT,
 status TEXT NOT NULL DEFAULT 'REVIEW'
);
'''

def now(): return datetime.now(timezone.utc).isoformat()
def db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    c=sqlite3.connect(DB_PATH, timeout=15); c.row_factory=sqlite3.Row; c.execute('PRAGMA journal_mode=WAL'); c.execute('PRAGMA foreign_keys=ON'); return c

def init_db():
    c=db(); c.executescript(SCHEMA)
    # Safe migration for older starter databases.
    cols={r['name'] for r in c.execute('PRAGMA table_info(orders)')}
    for name,typ in [('user_id','INTEGER'),('provider_order_id','TEXT'),('provider_payment_id','TEXT'),('assigned_rider_id','INTEGER'),('assigned_at','TEXT'),('picked_up_at','TEXT'),('delivered_at','TEXT')]:
        if name not in cols: c.execute(f'ALTER TABLE orders ADD COLUMN {name} {typ}')
    pcols={r['name'] for r in c.execute('PRAGMA table_info(partners)')}
    for name,typ in [('latitude','REAL'),('longitude','REAL'),('google_place_id','TEXT'),('source',"TEXT NOT NULL DEFAULT 'TAZVIKO'"),('pin_hash','TEXT'),('opening_hours','TEXT'),('delivery_radius_km','INTEGER NOT NULL DEFAULT 5'),('logo_url','TEXT')]:
        if name not in pcols: c.execute(f'ALTER TABLE partners ADD COLUMN {name} {typ}')
    product_cols={r['name'] for r in c.execute('PRAGMA table_info(products)')}
    for name,typ in [('partner_id','INTEGER'),('category','TEXT'),('description','TEXT'),('image_url','TEXT'),('stock_qty','INTEGER NOT NULL DEFAULT 100')]:
        if name not in product_cols: c.execute(f'ALTER TABLE products ADD COLUMN {name} {typ}')
    seed_products=[
        ('spice-junction-paneer-combo','Paneer Combo','Spice Junction',249),
        ('pizza-town-farmhouse-pizza','Farmhouse Pizza','Pizza Town',299),
        ('biryani-house-biryani-meal','Biryani Meal','Biryani House',279),
        ('sweet-crumbs-dessert-box','Dessert Box','Sweet Crumbs',189),
        ('fresh-basket-produce','Fresh Produce Basket','Fresh Basket',299),
        ('daily-needs-breakfast','Breakfast Essentials','Daily Needs',219),
        ('care-point-wellness','Wellness Essentials','Care Point',349),
        ('city-mall-store-item','Mall Store Item','City Mall Store',499),
    ]
    c.executemany('INSERT OR IGNORE INTO products(product_key,name,merchant,price,active) VALUES(?,?,?,?,1)',seed_products)
    seed_coupons=[
        ('WELCOME50','PERCENT',5000,1,150,1),
        ('GROCERY100','FLAT',100,799,100,1),
        ('FREEDEL','FREE_DELIVERY',0,1,0,1),
        ('TAZVIKO100','FLAT',100,299,100,1),
    ]
    c.executemany('INSERT OR REPLACE INTO coupons(code,discount_type,discount_value,min_subtotal,max_discount,active) VALUES(?,?,?,?,?,?)', seed_coupons)
    c.commit(); c.close()

def calculate_order(items,coupon_code=''):
    if not isinstance(items,list) or not items:
        raise ValueError('empty_cart')
    c=db(); normalized=[]; subtotal=0
    try:
        for raw in items:
            if not isinstance(raw,dict): raise ValueError('invalid_item')
            qty=int(raw.get('qty',0))
            if qty < 1 or qty > 25: raise ValueError('invalid_quantity')
            key=str(raw.get('product_key','')).strip()
            row=None
            if key:
                row=c.execute('SELECT * FROM products WHERE product_key=? AND active=1',(key,)).fetchone()
            if row is None:
                name=str(raw.get('name','')).strip(); merchant=str(raw.get('merchant','')).strip()
                row=c.execute('SELECT * FROM products WHERE name=? AND merchant=? AND active=1',(name,merchant)).fetchone()
            if row is None or int(row['stock_qty'] if 'stock_qty' in row.keys() else 100)<qty: raise ValueError('product_not_available')
            line=int(row['price'])*qty; subtotal+=line
            normalized.append({'product_key':row['product_key'],'partner_id':row['partner_id'] if 'partner_id' in row.keys() else None,'name':row['name'],'merchant':row['merchant'],'price':int(row['price']),'qty':qty,'line_total':line})
        discount=0; applied_coupon=''
        code=str(coupon_code or '').strip().upper()
        if code:
            cp=c.execute('SELECT * FROM coupons WHERE code=? AND active=1',(code,)).fetchone()
            if cp and subtotal >= int(cp['min_subtotal']):
                if cp['discount_type']=='FLAT': discount=int(cp['discount_value'])
                elif cp['discount_type']=='PERCENT': discount=(subtotal*int(cp['discount_value']))//10000
                cap=int(cp['max_discount'] or 0)
                if cap: discount=min(discount,cap)
                discount=min(discount,subtotal); applied_coupon=code
        delivery=DELIVERY_FEE if subtotal else 0
        if applied_coupon:
            cp2=c.execute('SELECT discount_type FROM coupons WHERE code=?',(applied_coupon,)).fetchone()
            if cp2 and cp2['discount_type']=='FREE_DELIVERY': delivery=0
        platform=PLATFORM_FEE if subtotal else 0
        tax=(subtotal*TAX_BPS + 5000)//10000
        commission=(subtotal*COMMISSION_BPS + 5000)//10000
        merchant_payable=max(0,subtotal-commission)
        total=max(0,subtotal+delivery+platform+tax-discount)
        earning=commission+delivery+platform
        return {'items':normalized,'subtotal':subtotal,'discount':discount,'delivery_fee':delivery,'platform_fee':platform,'tax':tax,'total':total,'commission':commission,'merchant_payable':merchant_payable,'tazviko_earning':earning,'coupon':applied_coupon}
    finally:
        c.close()

def rowdict(row):
    d=dict(row)
    if 'items_json' in d:
        try: d['items']=json.loads(d.pop('items_json'))
        except Exception: d['items']=[]
    return d

def hash_pin(pin,salt=None):
    salt=salt or secrets.token_bytes(16)
    dk=hashlib.pbkdf2_hmac('sha256',pin.encode(),salt,180000)
    return base64.b64encode(salt).decode()+':'+base64.b64encode(dk).decode()

def check_pin(pin,stored):
    try:
        s,d=stored.split(':',1); salt=base64.b64decode(s); expected=base64.b64decode(d)
        got=hashlib.pbkdf2_hmac('sha256',pin.encode(),salt,180000)
        return hmac.compare_digest(got,expected)
    except Exception:return False

def new_session(uid):
    token=secrets.token_urlsafe(32); exp=datetime.now(timezone.utc)+timedelta(days=30)
    c=db(); c.execute('INSERT INTO sessions(token,user_id,created_at,expires_at) VALUES(?,?,?,?)',(token,uid,now(),exp.isoformat())); c.commit(); c.close(); return token

def session_user(handler):
    auth=handler.headers.get('Authorization','')
    token=auth[7:] if auth.startswith('Bearer ') else ''
    if not token:return None
    c=db(); r=c.execute('''SELECT u.* FROM sessions s JOIN users u ON u.id=s.user_id WHERE s.token=? AND s.expires_at>?''',(token,now())).fetchone(); c.close(); return dict(r) if r else None

def valid_admin(handler,qs=None):
    key=handler.headers.get('X-Admin-Key','')
    return bool(key) and hmac.compare_digest(key,ADMIN_KEY)

def rate_ok(handler):
    ip=handler.client_address[0] if handler.client_address else 'unknown'
    bucket=int(time.time()//60)
    with _rate_lock:
        key=(ip,bucket); _rate[key]=_rate.get(key,0)+1
        if len(_rate)>5000:
            for k in list(_rate):
                if k[1] < bucket-2: _rate.pop(k,None)
        return _rate[key] <= RATE_LIMIT

def same_origin(handler):
    origin=handler.headers.get('Origin')
    host=handler.headers.get('Host','')
    if not origin: return True
    try: return urlparse(origin).netloc == host
    except Exception: return False

def new_rider_session(rider_id):
    token=secrets.token_urlsafe(32); exp=datetime.now(timezone.utc)+timedelta(days=30)
    c=db(); c.execute('INSERT INTO rider_sessions(token,rider_id,created_at,expires_at) VALUES(?,?,?,?)',(token,rider_id,now(),exp.isoformat())); c.commit(); c.close(); return token

def new_merchant_session(partner_id):
    token=secrets.token_urlsafe(32); exp=datetime.now(timezone.utc)+timedelta(days=30)
    c=db(); c.execute('INSERT INTO merchant_sessions(token,partner_id,created_at,expires_at) VALUES(?,?,?,?)',(token,partner_id,now(),exp.isoformat())); c.commit(); c.close(); return token

def merchant_user(handler):
    auth=handler.headers.get('Authorization',''); token=auth[7:] if auth.startswith('Bearer ') else ''
    if not token:return None
    c=db(); r=c.execute("SELECT p.* FROM merchant_sessions s JOIN partners p ON p.id=s.partner_id WHERE s.token=? AND s.expires_at>? AND p.status='LIVE'",(token,now())).fetchone(); c.close(); return dict(r) if r else None

def merchant_orders(partner_id):
    c=db(); rows=[]
    for r in c.execute('SELECT * FROM orders ORDER BY id DESC LIMIT 500'):
        item=rowdict(r)
        if any(int(x.get('partner_id') or 0)==int(partner_id) for x in item.get('items',[])): rows.append(item)
    c.close(); return rows

def rider_user(handler):
    auth=handler.headers.get('Authorization','')
    token=auth[7:] if auth.startswith('Bearer ') else ''
    if not token:return None
    c=db(); r=c.execute("SELECT r.* FROM rider_sessions s JOIN riders r ON r.id=s.rider_id WHERE s.token=? AND s.expires_at>? AND r.status='ACTIVE'",(token,now())).fetchone(); c.close(); return dict(r) if r else None

def google_nearby(lat,lng,radius=4000,category='all'):
    if not GOOGLE_PLACES_API_KEY: return None
    category_map={
      'food':['restaurant','cafe','bakery','meal_takeaway'],
      'grocery':['grocery_store','supermarket','convenience_store'],
      'mall':['shopping_mall','department_store'],
      'pharmacy':['pharmacy','drugstore'],
      'shop':['store','clothing_store','electronics_store','jewelry_store'],
      'all':['restaurant','cafe','bakery','grocery_store','supermarket','convenience_store','shopping_mall','department_store','pharmacy','store']
    }
    types=category_map.get(category,category_map['all'])[:50]
    payload={'includedTypes':types,'maxResultCount':20,'locationRestriction':{'circle':{'center':{'latitude':float(lat),'longitude':float(lng)},'radius':float(max(100,min(int(radius),10000)))}}}
    raw=json.dumps(payload).encode()
    fields='places.id,places.displayName,places.formattedAddress,places.location,places.primaryType,places.rating,places.currentOpeningHours.openNow,places.googleMapsLinks.placeUri'
    req=urllib.request.Request('https://places.googleapis.com/v1/places:searchNearby',data=raw,headers={'Content-Type':'application/json','X-Goog-Api-Key':GOOGLE_PLACES_API_KEY,'X-Goog-FieldMask':fields},method='POST')
    with urllib.request.urlopen(req,timeout=15) as resp: data=json.loads(resp.read().decode())
    out=[]
    for x in data.get('places',[]):
        loc=x.get('location') or {}; nm=(x.get('displayName') or {}).get('text','')
        out.append({'place_id':x.get('id',''),'name':nm,'address':x.get('formattedAddress',''),'latitude':loc.get('latitude'),'longitude':loc.get('longitude'),'type':x.get('primaryType',''),'rating':x.get('rating'),'open_now':((x.get('currentOpeningHours') or {}).get('openNow')),'maps_url':((x.get('googleMapsLinks') or {}).get('placeUri')),'source':'GOOGLE','orderable':False})
    c=db(); live={r['google_place_id']:dict(r) for r in c.execute("SELECT * FROM partners WHERE status='LIVE' AND google_place_id IS NOT NULL AND google_place_id<>''")}; c.close()
    for x in out:
        if x['place_id'] in live:
            x['orderable']=True; x['partner_id']=live[x['place_id']]['id']
    return out

def razorpay_request(path,payload):
    if not (RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET): raise RuntimeError('payment_gateway_not_configured')
    raw=json.dumps(payload).encode(); token=base64.b64encode(f'{RAZORPAY_KEY_ID}:{RAZORPAY_KEY_SECRET}'.encode()).decode()
    req=urllib.request.Request('https://api.razorpay.com/v1'+path,data=raw,headers={'Content-Type':'application/json','Authorization':'Basic '+token},method='POST')
    try:
        with urllib.request.urlopen(req,timeout=20) as resp: return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        try: detail=json.loads(e.read().decode())
        except Exception: detail={'error':'gateway_error'}
        raise RuntimeError(json.dumps(detail))

class Handler(SimpleHTTPRequestHandler):
    def _security_headers(self):
        self.send_header('X-Content-Type-Options','nosniff')
        self.send_header('X-Frame-Options','DENY')
        self.send_header('Referrer-Policy','strict-origin-when-cross-origin')
        self.send_header('Permissions-Policy','camera=(), microphone=(), geolocation=(self)')
        self.send_header('Cross-Origin-Opener-Policy','same-origin')
        if PUBLIC_BASE_URL.startswith('https://'):
            self.send_header('Strict-Transport-Security','max-age=31536000; includeSubDomains')
    def end_headers(self):
        self._security_headers(); super().end_headers()
    def translate_path(self,path):
        p=urlparse(path).path
        if p=='/': p='/index.html'
        target=(ROOT/p.lstrip('/')).resolve()
        if ROOT not in target.parents and target!=ROOT:return str(ROOT/'index.html')
        return str(target)
    def send_json(self,obj,status=200):
        data=json.dumps(obj,ensure_ascii=False).encode(); self.send_response(status); self.send_header('Content-Type','application/json; charset=utf-8'); self.send_header('Content-Length',str(len(data))); self.send_header('Cache-Control','no-store'); self.end_headers(); self.wfile.write(data)
    def read_json(self):
        try:
            n=int(self.headers.get('Content-Length','0'))
            if n<0 or n>MAX_BODY: return None
            return json.loads(self.rfile.read(n) or b'{}')
        except Exception:return None
    def _guard(self, mutate=False):
        if not rate_ok(self): self.send_json({'error':'rate_limited'},429); return False
        if mutate and not same_origin(self): self.send_json({'error':'invalid_origin'},403); return False
        return True
    def do_GET(self):
        if not self._guard(): return
        u=urlparse(self.path); p=u.path; qs=parse_qs(u.query)
        if p=='/api/v1/health': return self.send_json({'ok':True,'mode':'launch-ready','payment_gateway':'razorpay' if RAZORPAY_KEY_ID else 'not-configured','time':now()})
        if p=='/api/v1/config': return self.send_json({'app_name':'TAZVIKO','currency':'INR','online_payment_enabled':bool(RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET),'razorpay_key_id':RAZORPAY_KEY_ID,'nearby_discovery_enabled':bool(GOOGLE_PLACES_API_KEY),'rider_portal':'/rider.html','merchant_portal':'/partner.html'})
        if p=='/api/v1/catalog':
            c=db(); rows=[dict(r) for r in c.execute("SELECT pr.product_key,pr.name,pr.merchant,pr.price,pr.category,pr.description,pr.image_url,pr.stock_qty,pr.partner_id FROM products pr LEFT JOIN partners p ON p.id=pr.partner_id WHERE pr.active=1 AND pr.stock_qty>0 AND (pr.partner_id IS NULL OR p.status='LIVE') ORDER BY pr.partner_id DESC,pr.merchant,pr.name")]; c.close(); return self.send_json({'products':rows})
        if p=='/api/v1/partners/live':
            c=db(); rows=[{k:v for k,v in dict(r).items() if k!='pin_hash'} for r in c.execute("SELECT * FROM partners WHERE status='LIVE' ORDER BY id DESC")]; c.close(); return self.send_json({'partners':rows})
        if p=='/api/v1/merchant/me':
            m=merchant_user(self); return self.send_json({'merchant':{k:v for k,v in m.items() if k!='pin_hash'}}) if m else self.send_json({'error':'merchant_login_required'},401)
        if p=='/api/v1/merchant/products':
            m=merchant_user(self)
            if not m:return self.send_json({'error':'merchant_login_required'},401)
            c=db(); rows=[dict(r) for r in c.execute('SELECT * FROM products WHERE partner_id=? ORDER BY id DESC',(m['id'],))]; c.close(); return self.send_json({'products':rows})
        if p=='/api/v1/merchant/orders':
            m=merchant_user(self)
            if not m:return self.send_json({'error':'merchant_login_required'},401)
            return self.send_json({'orders':merchant_orders(m['id'])})
        if p=='/api/v1/merchant/stats':
            m=merchant_user(self)
            if not m:return self.send_json({'error':'merchant_login_required'},401)
            orders=merchant_orders(m['id']); sales=sum(int(o['subtotal']) for o in orders if o['status']!='CANCELLED'); open_count=sum(o['status'] not in ('DELIVERED','CANCELLED') for o in orders)
            c=db(); products=c.execute('SELECT COUNT(*) c FROM products WHERE partner_id=? AND active=1',(m['id'],)).fetchone()['c']; c.close(); return self.send_json({'orders':len(orders),'sales':sales,'open_orders':open_count,'products':products})
        if p=='/api/v1/auth/me':
            usr=session_user(self); return self.send_json({'user':usr},200 if usr else 401)
        if p=='/api/v1/places/nearby':
            try:
                lat=float((qs.get('lat') or [''])[0]); lng=float((qs.get('lng') or [''])[0]); radius=int((qs.get('radius') or ['4000'])[0]); category=str((qs.get('category') or ['all'])[0])
            except Exception:return self.send_json({'error':'valid_lat_lng_required'},400)
            try:
                rows=google_nearby(lat,lng,radius,category)
                if rows is None:
                    c=db(); rows=[dict(r) for r in c.execute("SELECT id AS partner_id,business_name AS name,address,city,business_type AS type,latitude,longitude,google_place_id AS place_id,status FROM partners WHERE status='LIVE' ORDER BY id DESC LIMIT 100")]; c.close()
                    for x in rows: x.update({'source':'TAZVIKO','orderable':True,'open_now':None})
                    return self.send_json({'provider':'TAZVIKO_ONLY','places':rows,'message':'Add GOOGLE_PLACES_API_KEY for automatic nearby business discovery.'})
                return self.send_json({'provider':'GOOGLE','places':rows})
            except Exception as e:return self.send_json({'error':'nearby_provider_error','detail':str(e)[:300]},502)
        if p=='/api/v1/rider/me':
            r=rider_user(self); return self.send_json({'rider':r},200 if r else 401)
        if p=='/api/v1/rider/orders':
            r=rider_user(self)
            if not r:return self.send_json({'error':'rider_login_required'},401)
            c=db(); rows=[rowdict(x) for x in c.execute("SELECT * FROM orders WHERE assigned_rider_id=? AND status NOT IN ('CANCELLED') ORDER BY CASE WHEN status='DELIVERED' THEN 1 ELSE 0 END,id DESC LIMIT 100",(r['id'],))]; c.close(); return self.send_json({'orders':rows})
        if p=='/api/v1/riders':
            if not valid_admin(self,qs):return self.send_json({'error':'admin_unauthorized'},401)
            c=db(); rows=[{k:v for k,v in dict(r).items() if k!='pin_hash'} for r in c.execute('SELECT * FROM riders ORDER BY id DESC')]; c.close(); return self.send_json({'riders':rows})
        if p=='/api/v1/orders/mine':
            usr=session_user(self)
            if not usr:return self.send_json({'error':'login_required'},401)
            c=db(); rows=[rowdict(r) for r in c.execute('SELECT * FROM orders WHERE user_id=? ORDER BY id DESC LIMIT 100',(usr['id'],))]; c.close(); return self.send_json({'orders':rows})
        if p=='/api/v1/orders':
            if not valid_admin(self,qs): return self.send_json({'error':'admin_unauthorized'},401)
            c=db(); rows=[rowdict(r) for r in c.execute('SELECT * FROM orders ORDER BY id DESC LIMIT 500')]; c.close(); return self.send_json({'orders':rows})
        if p=='/api/v1/partners/applications':
            if not valid_admin(self,qs): return self.send_json({'error':'admin_unauthorized'},401)
            c=db(); rows=[dict(r) for r in c.execute('SELECT * FROM partners ORDER BY id DESC LIMIT 500')]; c.close(); return self.send_json({'partners':rows})
        if p=='/api/v1/delivery/applications':
            if not valid_admin(self,qs): return self.send_json({'error':'admin_unauthorized'},401)
            c=db(); rows=[dict(r) for r in c.execute('SELECT * FROM delivery_applications ORDER BY id DESC LIMIT 500')]; c.close(); return self.send_json({'applications':rows})
        if p=='/api/v1/support/tickets':
            if not valid_admin(self,qs): return self.send_json({'error':'admin_unauthorized'},401)
            c=db(); rows=[dict(r) for r in c.execute('SELECT * FROM support_tickets ORDER BY id DESC LIMIT 500')]; c.close(); return self.send_json({'tickets':rows})
        if p=='/api/v1/admin/stats':
            if not valid_admin(self,qs): return self.send_json({'error':'admin_unauthorized'},401)
            c=db(); s=c.execute('''SELECT COUNT(*) c,COALESCE(SUM(subtotal),0) sales,COALESCE(SUM(tazviko_earning),0) earn,COALESCE(SUM(CASE WHEN payment_status='PAID' THEN total ELSE 0 END),0) paid FROM orders''').fetchone(); pending=c.execute("SELECT COUNT(*) c FROM orders WHERE status NOT IN ('DELIVERED','CANCELLED')").fetchone()['c']; partners=c.execute("SELECT COUNT(*) c FROM partners WHERE status='LIVE'").fetchone()['c']; c.close(); return self.send_json({'orders':s['c'],'sales':s['sales'],'earning':s['earn'],'online_collected':s['paid'],'open_orders':pending,'live_partners':partners})
        if p.startswith('/api/v1/orders/') and p.endswith('/tracking'):
            code=p.split('/')[-2]; c=db(); r=c.execute('SELECT order_code,status,payment_method,payment_status,created_at,total FROM orders WHERE order_code=?',(code,)).fetchone(); c.close(); return self.send_json(dict(r)) if r else self.send_json({'error':'not_found'},404)
        return super().do_GET()
    def do_POST(self):
        if not self._guard(mutate=True): return
        p=urlparse(self.path).path; data=self.read_json()
        if data is None:return self.send_json({'error':'invalid_json'},400)
        if p=='/api/v1/merchant/login':
            mobile=str(data.get('mobile','')).strip(); pin=str(data.get('pin','')).strip(); c=db(); m=c.execute("SELECT * FROM partners WHERE phone=? AND status='LIVE'",(mobile,)).fetchone(); c.close()
            if not m or not m['pin_hash'] or not check_pin(pin,m['pin_hash']):return self.send_json({'error':'invalid_merchant_login'},401)
            return self.send_json({'ok':True,'token':new_merchant_session(m['id']),'merchant':{'id':m['id'],'business_name':m['business_name'],'phone':m['phone']}})
        if p=='/api/v1/partners/activate':
            if not valid_admin(self):return self.send_json({'error':'admin_unauthorized'},401)
            try:partner_id=int(data.get('partner_id'))
            except Exception:return self.send_json({'error':'partner_id_required'},400)
            pin=str(data.get('pin','')).strip()
            if len(pin)<4:return self.send_json({'error':'merchant_pin_min_4'},400)
            c=db(); m=c.execute('SELECT * FROM partners WHERE id=?',(partner_id,)).fetchone()
            if not m:c.close();return self.send_json({'error':'partner_not_found'},404)
            if not str(m['phone'] or '').strip():c.close();return self.send_json({'error':'partner_mobile_required'},400)
            c.execute("UPDATE partners SET status='LIVE',pin_hash=? WHERE id=?",(hash_pin(pin),partner_id));c.commit();c.close();return self.send_json({'ok':True,'partner_id':partner_id,'mobile':m['phone'],'portal':'/partner.html'})
        if p=='/api/v1/merchant/products':
            m=merchant_user(self)
            if not m:return self.send_json({'error':'merchant_login_required'},401)
            name=str(data.get('name','')).strip(); category=str(data.get('category','')).strip(); image_url=str(data.get('image_url','')).strip(); description=str(data.get('description','')).strip()
            try:price=max(1,int(data.get('price'))); stock=max(0,int(data.get('stock_qty',0)))
            except Exception:return self.send_json({'error':'valid_price_stock_required'},400)
            if not name:return self.send_json({'error':'product_name_required'},400)
            key='p'+str(m['id'])+'-'+secrets.token_hex(6);c=db();cur=c.execute('INSERT INTO products(product_key,name,merchant,price,active,partner_id,category,description,image_url,stock_qty) VALUES(?,?,?,?,1,?,?,?,?,?)',(key,name[:150],m['business_name'][:150],price,m['id'],category[:80],description[:1000],image_url[:1000],stock));c.commit();pid=cur.lastrowid;c.close();return self.send_json({'ok':True,'id':pid,'product_key':key},201)
        if p=='/api/v1/rider/login':
            mobile=str(data.get('mobile','')).strip(); pin=str(data.get('pin','')).strip(); c=db(); r=c.execute("SELECT * FROM riders WHERE mobile=? AND status='ACTIVE'",(mobile,)).fetchone(); c.close()
            if not r or not check_pin(pin,r['pin_hash']):return self.send_json({'error':'invalid_rider_login'},401)
            return self.send_json({'ok':True,'token':new_rider_session(r['id']),'rider':{'id':r['id'],'full_name':r['full_name'],'mobile':r['mobile']}})
        if p=='/api/v1/riders/activate':
            if not valid_admin(self):return self.send_json({'error':'admin_unauthorized'},401)
            try:app_id=int(data.get('application_id'))
            except Exception:return self.send_json({'error':'application_id_required'},400)
            pin=str(data.get('pin','')).strip()
            if len(pin)<4:return self.send_json({'error':'rider_pin_min_4'},400)
            c=db(); a=c.execute('SELECT * FROM delivery_applications WHERE id=?',(app_id,)).fetchone()
            if not a:c.close(); return self.send_json({'error':'application_not_found'},404)
            try:
                cur=c.execute('INSERT INTO riders(created_at,full_name,mobile,pin_hash,status) VALUES(?,?,?,?,?)',(now(),a['full_name'],a['mobile'],hash_pin(pin),'ACTIVE')); rid=cur.lastrowid
            except sqlite3.IntegrityError:
                r=c.execute('SELECT id FROM riders WHERE mobile=?',(a['mobile'],)).fetchone(); rid=r['id']; c.execute("UPDATE riders SET full_name=?,pin_hash=?,status='ACTIVE' WHERE id=?",(a['full_name'],hash_pin(pin),rid))
            c.execute("UPDATE delivery_applications SET status='APPROVED' WHERE id=?",(app_id,)); c.commit(); c.close(); return self.send_json({'ok':True,'rider_id':rid,'mobile':a['mobile'],'portal':'/rider.html'},201)
        if p=='/api/v1/auth/register':
            name=str(data.get('name','')).strip(); mobile=str(data.get('mobile','')).strip(); pin=str(data.get('pin','')).strip(); email=str(data.get('email','')).strip()
            if not name or len(mobile)<8 or len(pin)<4:return self.send_json({'error':'name_mobile_pin_required'},400)
            try:
                c=db(); cur=c.execute('INSERT INTO users(created_at,name,mobile,email,pin_hash,status) VALUES(?,?,?,?,?,?)',(now(),name[:120],mobile[:30],email[:160],hash_pin(pin),'ACTIVE')); c.commit(); uid=cur.lastrowid; c.close()
            except sqlite3.IntegrityError:return self.send_json({'error':'mobile_already_registered'},409)
            return self.send_json({'ok':True,'token':new_session(uid),'user':{'id':uid,'name':name,'mobile':mobile,'email':email}},201)
        if p=='/api/v1/auth/login':
            mobile=str(data.get('mobile','')).strip(); pin=str(data.get('pin','')).strip(); c=db(); r=c.execute('SELECT * FROM users WHERE mobile=?',(mobile,)).fetchone(); c.close()
            if not r or not check_pin(pin,r['pin_hash']):return self.send_json({'error':'invalid_login'},401)
            return self.send_json({'ok':True,'token':new_session(r['id']),'user':{'id':r['id'],'name':r['name'],'mobile':r['mobile'],'email':r['email']}})
        if p=='/api/v1/quote':
            try: q=calculate_order(data.get('items'),data.get('coupon',''))
            except ValueError as e:return self.send_json({'error':str(e)},400)
            return self.send_json(q)
        if p=='/api/v1/orders':
            usr=session_user(self); required=['customer_name','mobile','address','items']
            if any(data.get(k) in (None,'',[]) for k in required):return self.send_json({'error':'missing_required_fields'},400)
            method=str(data.get('payment_method','COD')).upper()
            if method not in {'COD','RAZORPAY'}: return self.send_json({'error':'invalid_payment_method'},400)
            if method=='RAZORPAY' and not (RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET): return self.send_json({'error':'payment_gateway_not_configured'},503)
            try:q=calculate_order(data.get('items'),data.get('coupon',''))
            except ValueError as e:return self.send_json({'error':str(e)},400)
            merchants=sorted({x['merchant'] for x in q['items']}); merchant=' / '.join(merchants)[:150]
            code='TZ'+datetime.now().strftime('%y%m%d')+str(secrets.randbelow(9000)+1000); pstatus='COD_PENDING' if method=='COD' else 'AWAITING_PAYMENT'
            vals=(code,now(),usr['id'] if usr else None,str(data['customer_name'])[:120],str(data['mobile'])[:30],str(data['address'])[:500],merchant,json.dumps(q['items'],ensure_ascii=False),q['subtotal'],q['discount'],q['delivery_fee'],q['platform_fee'],q['tax'],q['total'],q['commission'],q['merchant_payable'],q['tazviko_earning'],method,pstatus,'PLACED')
            c=db(); c.execute('''INSERT INTO orders(order_code,created_at,user_id,customer_name,mobile,address,merchant,items_json,subtotal,discount,delivery_fee,platform_fee,tax,total,commission,merchant_payable,tazviko_earning,payment_method,payment_status,status) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)''',vals)
            for item in q['items']: c.execute('UPDATE products SET stock_qty=MAX(0,stock_qty-?) WHERE product_key=?',(item['qty'],item['product_key']))
            c.commit(); c.close(); return self.send_json({'ok':True,'order_code':code,'status':'PLACED','payment_status':pstatus,'quote':q},201)
        if p=='/api/v1/payments/create':
            code=str(data.get('order_code','')).strip(); c=db(); o=c.execute('SELECT * FROM orders WHERE order_code=?',(code,)).fetchone(); c.close()
            if not o:return self.send_json({'error':'order_not_found'},404)
            if o['payment_method']=='COD':return self.send_json({'error':'cod_order'},400)
            if not (RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET):return self.send_json({'error':'payment_gateway_not_configured'},503)
            receipt=code[:40]
            try:r=razorpay_request('/orders',{'amount':int(o['total'])*100,'currency':'INR','receipt':receipt,'notes':{'tazviko_order':code}})
            except Exception as e:return self.send_json({'error':'payment_gateway_error','detail':str(e)[:500]},502)
            c=db(); c.execute('UPDATE orders SET provider_order_id=? WHERE order_code=?',(r.get('id'),code)); c.commit(); c.close(); return self.send_json({'ok':True,'provider':'razorpay','key_id':RAZORPAY_KEY_ID,'razorpay_order_id':r.get('id'),'amount':r.get('amount'),'currency':'INR','order_code':code})
        if p=='/api/v1/payments/verify':
            code=str(data.get('order_code','')); ro=str(data.get('razorpay_order_id','')); rp=str(data.get('razorpay_payment_id','')); sig=str(data.get('razorpay_signature',''))
            if not all([code,ro,rp,sig,RAZORPAY_KEY_SECRET]):return self.send_json({'error':'missing_payment_verification'},400)
            expected=hmac.new(RAZORPAY_KEY_SECRET.encode(),f'{ro}|{rp}'.encode(),hashlib.sha256).hexdigest()
            if not hmac.compare_digest(expected,sig):return self.send_json({'error':'invalid_payment_signature'},400)
            c=db(); cur=c.execute("UPDATE orders SET payment_status='PAID',provider_order_id=?,provider_payment_id=? WHERE order_code=? AND provider_order_id=?",(ro,rp,code,ro)); c.commit(); c.close(); return self.send_json({'ok':cur.rowcount>0,'payment_status':'PAID'})
        if p=='/api/v1/support/tickets':
            usr=session_user(self); message=str(data.get('message','')).strip(); category=str(data.get('category','Other')).strip(); mobile=str(data.get('mobile','')).strip()
            if not message:return self.send_json({'error':'message_required'},400)
            c=db(); cur=c.execute('INSERT INTO support_tickets(created_at,user_id,mobile,category,message,status) VALUES(?,?,?,?,?,?)',(now(),usr['id'] if usr else None,mobile[:30],category[:80],message[:3000],'OPEN')); c.commit(); tid=cur.lastrowid; c.close(); return self.send_json({'ok':True,'ticket_id':tid,'status':'OPEN'},201)
        if p=='/api/v1/delivery/applications':
            full_name=str(data.get('full_name','')).strip(); mobile=str(data.get('mobile','')).strip()
            if not full_name or len(mobile)<8:return self.send_json({'error':'name_mobile_required'},400)
            c=db(); cur=c.execute('INSERT INTO delivery_applications(created_at,full_name,mobile,vehicle_type,vehicle_number,identity_ref,payout_ref,status) VALUES(?,?,?,?,?,?,?,?)',(now(),full_name[:120],mobile[:30],str(data.get('vehicle_type',''))[:60],str(data.get('vehicle_number',''))[:80],str(data.get('identity_ref',''))[:160],str(data.get('payout_ref',''))[:160],'REVIEW')); c.commit(); did=cur.lastrowid; c.close(); return self.send_json({'ok':True,'id':did,'status':'REVIEW'},201)
        if p=='/api/v1/partners/applications':
            if not data.get('business_name') or len(str(data.get('phone','')).strip())<8:return self.send_json({'error':'business_name_mobile_required'},400)
            c=db(); cur=c.execute('''INSERT INTO partners(created_at,business_name,owner_name,business_type,city,address,phone,bank_ref,catalog,status,latitude,longitude,google_place_id,source,opening_hours) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)''',(now(),str(data.get('business_name',''))[:150],str(data.get('owner_name',''))[:120],str(data.get('business_type',''))[:80],str(data.get('city',''))[:120],str(data.get('address',''))[:500],str(data.get('phone',''))[:30],str(data.get('bank_ref',''))[:160],str(data.get('catalog',''))[:5000],'REVIEW',data.get('latitude'),data.get('longitude'),str(data.get('google_place_id',''))[:200],str(data.get('source','TAZVIKO'))[:30],str(data.get('opening_hours',''))[:120])); c.commit(); pid=cur.lastrowid; c.close(); return self.send_json({'ok':True,'id':pid,'status':'REVIEW'},201)
        return self.send_json({'error':'not_found'},404)
    def do_PATCH(self):
        if not self._guard(mutate=True): return
        u=urlparse(self.path); p=u.path; qs=parse_qs(u.query); data=self.read_json() or {}
        if p=='/api/v1/merchant/profile':
            m=merchant_user(self)
            if not m:return self.send_json({'error':'merchant_login_required'},401)
            allowed={'business_name','owner_name','business_type','city','address','opening_hours','delivery_radius_km','logo_url','latitude','longitude'}; fields=[];vals=[]
            for k in allowed:
                if k in data:fields.append(k+'=?');vals.append(data[k])
            if not fields:return self.send_json({'error':'nothing_to_update'},400)
            vals.append(m['id']);c=db();c.execute('UPDATE partners SET '+','.join(fields)+' WHERE id=?',vals);c.execute('UPDATE products SET merchant=? WHERE partner_id=?',(str(data.get('business_name',m['business_name']))[:150],m['id']));c.commit();c.close();return self.send_json({'ok':True})
        if p.startswith('/api/v1/merchant/products/'):
            m=merchant_user(self)
            if not m:return self.send_json({'error':'merchant_login_required'},401)
            try:pid=int(p.rstrip('/').split('/')[-1])
            except Exception:return self.send_json({'error':'invalid_product_id'},400)
            allowed={'name','category','description','image_url','price','stock_qty','active'};fields=[];vals=[]
            for k in allowed:
                if k in data:fields.append(k+'=?');vals.append(data[k])
            if not fields:return self.send_json({'error':'nothing_to_update'},400)
            vals.extend([pid,m['id']]);c=db();cur=c.execute('UPDATE products SET '+','.join(fields)+' WHERE id=? AND partner_id=?',vals);c.commit();c.close();return self.send_json({'ok':cur.rowcount>0})
        if p.startswith('/api/v1/merchant/orders/') and p.endswith('/status'):
            m=merchant_user(self)
            if not m:return self.send_json({'error':'merchant_login_required'},401)
            code=p.split('/')[-2];status=str(data.get('status','')).upper();allowed={'CONFIRMED','PREPARING','READY','CANCELLED'}
            if status not in allowed:return self.send_json({'error':'invalid_merchant_status'},400)
            if not any(o['order_code']==code for o in merchant_orders(m['id'])):return self.send_json({'error':'order_not_for_merchant'},403)
            c=db();cur=c.execute("UPDATE orders SET status=? WHERE order_code=? AND status NOT IN ('PICKED_UP','ON_THE_WAY','DELIVERED')",(status,code));c.commit();c.close();return self.send_json({'ok':cur.rowcount>0,'status':status})
        if p.startswith('/api/v1/rider/orders/') and p.endswith('/status'):
            r=rider_user(self)
            if not r:return self.send_json({'error':'rider_login_required'},401)
            code=p.split('/')[-2]; status=str(data.get('status','')).upper(); allowed={'PICKED_UP','ON_THE_WAY','DELIVERED'}
            if status not in allowed:return self.send_json({'error':'invalid_rider_status'},400)
            c=db(); o=c.execute('SELECT assigned_rider_id FROM orders WHERE order_code=?',(code,)).fetchone()
            if not o or o['assigned_rider_id']!=r['id']:c.close(); return self.send_json({'error':'order_not_assigned_to_rider'},403)
            if status=='PICKED_UP': c.execute('UPDATE orders SET status=?,picked_up_at=? WHERE order_code=?',(status,now(),code))
            elif status=='DELIVERED': c.execute('UPDATE orders SET status=?,delivered_at=? WHERE order_code=?',(status,now(),code))
            else:c.execute('UPDATE orders SET status=? WHERE order_code=?',(status,code))
            c.commit(); c.close(); return self.send_json({'ok':True,'status':status,'order_code':code})
        if not valid_admin(self,qs):return self.send_json({'error':'admin_unauthorized'},401)
        if p.startswith('/api/v1/orders/') and p.endswith('/assign-rider'):
            code=p.split('/')[-2]
            try:rid=int(data.get('rider_id'))
            except Exception:return self.send_json({'error':'rider_id_required'},400)
            c=db(); rider=c.execute("SELECT id FROM riders WHERE id=? AND status='ACTIVE'",(rid,)).fetchone()
            if not rider:c.close(); return self.send_json({'error':'active_rider_not_found'},404)
            cur=c.execute('UPDATE orders SET assigned_rider_id=?,assigned_at=? WHERE order_code=?',(rid,now(),code)); c.commit(); c.close(); return self.send_json({'ok':cur.rowcount>0,'order_code':code,'rider_id':rid})
        if p.startswith('/api/v1/orders/') and p.endswith('/status'):
            code=p.split('/')[-2]; status=str(data.get('status','')).upper(); allowed={'PLACED','CONFIRMED','PREPARING','READY','PICKED_UP','ON_THE_WAY','DELIVERED','CANCELLED'}
            if status not in allowed:return self.send_json({'error':'invalid_status'},400)
            c=db(); cur=c.execute('UPDATE orders SET status=? WHERE order_code=?',(status,code)); c.commit(); c.close(); return self.send_json({'ok':cur.rowcount>0,'status':status})
        if p.startswith('/api/v1/support/tickets/'):
            try:tid=int(p.rstrip('/').split('/')[-1])
            except Exception:return self.send_json({'error':'invalid_id'},400)
            status=str(data.get('status','OPEN')).upper()
            if status not in {'OPEN','IN_PROGRESS','RESOLVED','CLOSED'}:return self.send_json({'error':'invalid_status'},400)
            c=db(); cur=c.execute('UPDATE support_tickets SET status=? WHERE id=?',(status,tid)); c.commit(); c.close(); return self.send_json({'ok':cur.rowcount>0,'status':status})
        if p.startswith('/api/v1/delivery/applications/'):
            try:did=int(p.rstrip('/').split('/')[-1])
            except Exception:return self.send_json({'error':'invalid_id'},400)
            status=str(data.get('status','REVIEW')).upper()
            if status not in {'REVIEW','APPROVED','REJECTED','SUSPENDED'}:return self.send_json({'error':'invalid_status'},400)
            c=db(); cur=c.execute('UPDATE delivery_applications SET status=? WHERE id=?',(status,did)); c.commit(); c.close(); return self.send_json({'ok':cur.rowcount>0,'status':status})
        if p.startswith('/api/v1/partners/applications/'):
            try:pid=int(p.rstrip('/').split('/')[-1])
            except Exception:return self.send_json({'error':'invalid_id'},400)
            status=str(data.get('status','LIVE')).upper()
            if status not in {'REVIEW','LIVE','REJECTED','SUSPENDED'}:return self.send_json({'error':'invalid_status'},400)
            c=db(); cur=c.execute('UPDATE partners SET status=? WHERE id=?',(status,pid)); c.commit(); c.close(); return self.send_json({'ok':cur.rowcount>0,'status':status})
        return self.send_json({'error':'not_found'},404)

if __name__=='__main__':
    if PUBLIC_BASE_URL and ADMIN_KEY=='change-me-now':
        raise SystemExit('Refusing public deployment with default TAZVIKO_ADMIN_KEY. Set a strong secret first.')
    init_db(); print(f'TAZVIKO launch-ready server: http://localhost:{PORT}'); print('Admin: /admin.html')
    if ADMIN_KEY=='change-me-now':print('WARNING: set TAZVIKO_ADMIN_KEY before public deployment.')
    print('Online payment:', 'ENABLED' if RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET else 'NOT CONFIGURED (COD still works)')
    os.chdir(ROOT); ThreadingHTTPServer(('0.0.0.0',PORT),Handler).serve_forever()
