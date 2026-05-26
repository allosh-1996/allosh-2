import json, os, time, hashlib, secrets, urllib.request, urllib.error
LAST_MGS = {}
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

DATA_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'allosh_data.json')
USERS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'users.json')
TOKENS = {}

DEVICE_IDS = {
    "idfa":           "E498C3EC-84E3-474B-A4AA-C22ED0F463CB",
    "idfv":           "814F8F95-096C-4C70-869C-360B490E7979",
    "iosver":         "16.7.12",
    "swId":           "95d96ad3-3114-411f-98f7-e821b3eab913",
    "installDate":    "2026-05-23",
    "unityIdfi":      "6928D137-F920-43E5-AE3B-66085B75D5B2",
    "unityPlayerId":  "7tGHCmw8yTdPvtEwWpEhdAcvDUEP",
    "unityUserId":    "ff274f67-8aab-942e-ebc7-7983e1ccc35e",
    "conversionData": "{\"is_universal_link\":null,\"media_source\":\"adjoe_int\",\"clickid\":\"d4905d64-477f-4401-acd9-2445d3f47f81\",\"iscache\":true,\"af_lang\":\"en-US\",\"af_ua\":\"Mozilla\\/5.0 (iPhone; CPU iPhone OS 16_7_12 like Mac OS X) AppleWebKit\\/605.1.15 (KHTML, like Gecko) Mobile\\/15E148\",\"orig_cost\":\"3.5\",\"af_ref\":\"adjoe_d4905d64-477f-4401-acd9-2445d3f47f81\",\"campaign_id\":\"9ba9db6a-513e-4888-a177-526f1e437d43\",\"campaign\":\"DISA_US_IOS_PREMIUM_EVENT-BASED\",\"af_pmod_lookback_window\":\"12h\",\"engmnt_source\":null,\"af_siteid\":\"ab2e6e83-5eca-43b5-9f8b-1ec8c02f6810\",\"adgroup_id\":null,\"af_cost_value\":\"3.50\",\"af_ad\":\"DISA^PinkHouse-New^1920x1080#ST000008582.png\",\"adset\":null,\"advertising_id\":\"E498C3EC-84E3-474B-A4AA-C22ED0F463CB\",\"is_incentivized\":\"false\",\"esp_name\":null,\"adset_id\":null,\"af_ad_type\":\"offerwall\",\"redirect_response_data\":null,\"af_adset_id\":\"ca2cda26-a4ba-4773-963c-247786370153\",\"af_status\":\"Non-organic\",\"af_cpi\":null,\"af_cost_currency\":\"USD\",\"af_sub3\":null,\"af_sub1\":null,\"af_ad_tran_id\":\"b1d841fc-9dab-42e9-8c1b-b8fa3b331d8a\",\"af_sub4\":null,\"retargeting_conversion_type\":\"none\",\"af_sub5\":null,\"install_time\":\"2026-05-23 14:18:13.877\",\"af_ad_id\":\"573160bc-e52c-411e-81c9-4a44b1e2fd22\",\"af_sub2\":null,\"is_first_launch\":false,\"adgroup\":null,\"cost_cents_USD\":\"350\",\"is_retargeting\":\"false\",\"af_c_id\":\"9ba9db6a-513e-4888-a177-526f1e437d43\",\"af_os_version\":\"16.7.12\",\"af_ip\":\"172.59.212.190\",\"af_click_lookback\":\"7d\",\"idfa\":\"E498C3EC-84E3-474B-A4AA-C22ED0F463CB\",\"agency\":null,\"af_cost_model\":\"CPI\",\"http_referrer\":null,\"is_branded_link\":null,\"af_adset\":\"DISA_US_IOS_PREMIUM_EVENT-BASED\",\"match_type\":\"id_matching\",\"CB_preload_equal_priority_enabled\":false,\"af_model\":\"iphone\",\"redirect\":\"false\",\"click_time\":\"2026-05-23 14:13:01.658\"}"
}

def load_json(path, default):
    try:
        with open(path) as f: return json.load(f)
    except: return default

def save_json(path, data):
    with open(path, 'w') as f: json.dump(data, f)

def hash_pw(pw):
    return hashlib.sha256(pw.encode()).hexdigest()

# Init default admin user
if not os.path.exists(USERS_FILE):
    save_json(USERS_FILE, [{"username": "admin", "password": hash_pw("admin123"), "role": "admin"}])

if not os.path.exists(DATA_FILE):
    save_json(DATA_FILE, {})

with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'index.html')) as f:
    HTML = f.read()

# Build manifest with base64 icons
import base64
with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'icons/icon-192.png'),'rb') as f: i192 = base64.b64encode(f.read()).decode()
with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'icons/icon-512.png'),'rb') as f: i512 = base64.b64encode(f.read()).decode()
ICON192 = base64.b64decode(i192)
ICON512 = base64.b64decode(i512)
MANIFEST = json.dumps({
    "name": "Allosh", "short_name": "Allosh",
    "start_url": "/", "display": "standalone",
    "background_color": "#0a0a1a", "theme_color": "#6366f1",
    "icons": [
        {"src": "/icon-192.png", "sizes": "192x192", "type": "image/png"},
        {"src": "/icon-512.png", "sizes": "512x512", "type": "image/png"}
    ]
})

class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a): pass

    def send_json(self, code, data):
        body = json.dumps(data).encode()
        self.send_response(code)
        self.send_header('Content-Type','application/json')
        self.send_header('Content-Length', len(body))
        self.send_header('Access-Control-Allow-Origin','*')
        self.end_headers()
        self.wfile.write(body)

    def get_token(self):
        auth = self.headers.get('Authorization','')
        if auth.startswith('Bearer '): return auth[7:]
        return None

    def get_user(self):
        tok = self.get_token()
        return TOKENS.get(tok)

    def read_body(self):
        l = int(self.headers.get('Content-Length', 0))
        return json.loads(self.rfile.read(l)) if l else {}

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header('Access-Control-Allow-Origin','*')
        self.send_header('Access-Control-Allow-Methods','GET,POST,DELETE,OPTIONS')
        self.send_header('Access-Control-Allow-Headers','Content-Type,Authorization')
        self.end_headers()

    def do_GET(self):
        p = urlparse(self.path).path
        qs = parse_qs(urlparse(self.path).query)

        if p == '/':
            body = HTML.encode()
            self.send_response(200)
            self.send_header('Content-Type','text/html; charset=utf-8')
            self.send_header('Content-Length', len(body))
            self.end_headers()
            self.wfile.write(body)

        elif p == '/manifest.json':
            body = MANIFEST.encode()
            self.send_response(200)
            self.send_header('Content-Type','application/manifest+json')
            self.send_header('Content-Length', len(body))
            self.end_headers()
            self.wfile.write(body)

        elif p == '/icon-192.png':
            self.send_response(200)
            self.send_header('Content-Type','image/png')
            self.send_header('Content-Length', len(ICON192))
            self.end_headers()
            self.wfile.write(ICON192)

        elif p == '/icon-512.png':
            self.send_response(200)
            self.send_header('Content-Type','image/png')
            self.send_header('Content-Length', len(ICON512))
            self.end_headers()
            self.wfile.write(ICON512)

        elif p == '/sw.js':
            body = b"self.addEventListener('fetch', e => e.respondWith(fetch(e.request)));"
            self.send_response(200)
            self.send_header('Content-Type','application/javascript')
            self.send_header('Content-Length', len(body))
            self.end_headers()
            self.wfile.write(body)

        elif p == '/api/me':
            u = self.get_user()
            if not u: self.send_json(401, {'error': 'Not authenticated'})
            else: self.send_json(200, {'username': u['username'], 'role': u['role']})

        elif p == '/api/data':
            u = self.get_user()
            if not u: return self.send_json(401, {'error': 'Unauthorized'})
            target = qs.get('user', [None])[0]
            if target and u['role'] == 'admin': key = target
            else: key = u['username']
            db = load_json(DATA_FILE, {})
            user_data = db.get(key, {'devices': []})
            # حقن الـ IDs تلقائياً لكل جهاز
            for dev in user_data.get('devices', []):
                if not dev.get('ids'):
                    dev['ids'] = DEVICE_IDS
                else:
                    for k, v in DEVICE_IDS.items():
                        if not dev['ids'].get(k):
                            dev['ids'][k] = v
            self.send_json(200, user_data)

        elif p == '/api/users':
            u = self.get_user()
            if not u or u['role'] != 'admin': return self.send_json(403, {'error': 'Forbidden'})
            users = load_json(USERS_FILE, [])
            db = load_json(DATA_FILE, {})
            result = []
            for usr in users:
                udb = db.get(usr['username'], {'devices': []})
                tasks = sum(len(g.get('tasks',[])) for d in udb.get('devices',[]) for s in d.get('sites',[]) for g in s.get('games',[]))
                result.append({'username': usr['username'], 'role': usr['role'], 'devices': len(udb.get('devices',[])), 'tasks': tasks})
            self.send_json(200, result)
        elif p == '/api/debug':
            self.send_json(200, {'last_mgs': LAST_MGS})
        else:
            self.send_json(404, {'error': 'Not found'})

    def do_POST(self):
        p = urlparse(self.path).path
        body = self.read_body()

        if p == '/api/login':
            users = load_json(USERS_FILE, [])
            u = next((x for x in users if x['username'] == body.get('username') and x['password'] == hash_pw(body.get('password',''))), None)
            if not u: return self.send_json(401, {'error': 'Wrong username or password'})
            tok = secrets.token_hex(32)
            TOKENS[tok] = {'username': u['username'], 'role': u['role']}
            self.send_json(200, {'token': tok, 'username': u['username'], 'role': u['role']})

        elif p == '/api/logout':
            tok = self.get_token()
            if tok: TOKENS.pop(tok, None)
            self.send_json(200, {'ok': True})

        elif p == '/api/data':
            u = self.get_user()
            if not u: return self.send_json(401, {'error': 'Unauthorized'})
            db = load_json(DATA_FILE, {})
            db[u['username']] = body
            save_json(DATA_FILE, db)
            self.send_json(200, {'ok': True})

        elif p == '/api/users':
            u = self.get_user()
            if not u or u['role'] != 'admin': return self.send_json(403, {'error': 'Forbidden'})
            users = load_json(USERS_FILE, [])
            if any(x['username'] == body.get('username') for x in users):
                return self.send_json(400, {'error': 'User already exists'})
            users.append({'username': body['username'], 'password': hash_pw(body['password']), 'role': 'user'})
            save_json(USERS_FILE, users)
            self.send_json(200, {'ok': True})
        elif p == '/api/mp':
            u = self.get_user()
            if not u: return self.send_json(401, {'error': 'Unauthorized'})
            token      = body.get('token', '')
            distinct_id = body.get('distinct_id', '')
            event      = body.get('event', '')
            properties = body.get('properties', {})
            if not token or not distinct_id or not event:
                return self.send_json(400, {'error': 'Missing fields'})
            import base64, time as _time
            properties['token']       = token
            properties['distinct_id'] = distinct_id
            properties['time']        = int(_time.time() * 1000)
            mp_event_id = hashlib.md5(str(_time.time()).encode()).hexdigest()[:8]
            payload_json = json.dumps([{
                'event': event,
                'properties': properties,
                '$mp_metadata': {
                    '$mp_event_id': mp_event_id,
                    '$mp_session_id': mp_event_id,
                    '$mp_session_seq_id': 1,
                    '$mp_session_start_sec': int(_time.time())
                }
            }])
            req = urllib.request.Request(
                'https://api-secure.mixpanel.com/track/?ip=1',
                data=payload_json.encode(),
                headers={
                    'Content-Type': 'application/json',
                    'Accept': '*/*',
                    'User-Agent': 'DisneySolitaire/2245 CFNetwork/3826.600.41.2.1 Darwin/24.6.0',
                    'Accept-Language': 'en-US,en;q=0.9',
                    'Accept-Encoding': 'gzip, deflate, br',
                    'x-unity-version': '2021.3.56f2'
                },
                method='POST'
            )
            try:
                with urllib.request.urlopen(req, timeout=10) as resp:
                    resp_body = resp.read().decode()
                    self.send_json(resp.status, {'status': resp.status, 'ok': True, 'body': resp_body})
            except urllib.error.HTTPError as e:
                body_err = e.read().decode()
                self.send_json(200, {'status': e.code, 'ok': False, 'error': body_err})
            except Exception as ex:
                self.send_json(200, {'status': 0, 'ok': False, 'error': str(ex)})
        elif p == '/api/af':
            u = self.get_user()
            if not u: return self.send_json(401, {'error': 'Unauthorized'})
            app_id  = body.get('app_id', '')
            dev_key = body.get('dev_key', '')
            payload = body.get('payload', {})
            if not app_id or not dev_key or not payload:
                return self.send_json(400, {'error': 'Missing app_id, dev_key or payload'})
            af_url = 'https://api2.appsflyer.com/inappevent/' + app_id
            print(f'[AF] URL: {af_url}')
            print(f'[AF] dev_key: {dev_key[:20]}...')
            print(f'[AF] appsflyer_id: {payload.get("appsflyer_id","")}')
            print(f'[AF] advertising_id: {payload.get("advertising_id","")}')
            print(f'[AF] eventName: {payload.get("eventName","")}')
            print(f'[AF] Full payload: {json.dumps(payload)[:500]}')
            req = urllib.request.Request(
                af_url,
                data=json.dumps(payload).encode(),
                headers={'Content-Type': 'application/json', 'authentication': dev_key},
                method='POST'
            )
            try:
                with urllib.request.urlopen(req, timeout=10) as resp:
                    resp_body = resp.read().decode()
                    print(f'[AF] Response: {resp.status} — {resp_body}')
                    self.send_json(resp.status, {'status': resp.status, 'ok': True, 'body': resp_body})
            except urllib.error.HTTPError as e:
                body_err = e.read().decode()
                print(f'[AF] HTTPError: {e.code} — {body_err}')
                self.send_json(200, {'status': e.code, 'ok': False, 'error': body_err})
            except Exception as ex:
                print(f'[AF] Exception: {ex}')
                self.send_json(200, {'status': 0, 'ok': False, 'error': str(ex)})
        elif p == '/api/mgs':
            u = self.get_user()
            if not u: return self.send_json(401, {'error': 'Unauthorized'})
            url     = body.get('url', '')
            payload = body.get('payload', {})
            if not url or not payload:
                return self.send_json(400, {'error': 'Missing url or payload'})
            import sys
            print(f'[MGS] URL: {url}', flush=True)
            if payload.get('events'):
                ev = payload['events'][0]
                print(f'[MGS] FULL EVENT: {json.dumps(ev)}', flush=True)
                sys.stdout.flush()
            req = urllib.request.Request(
                url,
                data=json.dumps(payload).encode(),
                headers={
                    'Content-Type': 'application/json',
                    'accept': '*/*',
                    'accept-language': 'en-US,en;q=0.9',
                    'user-agent': 'ScrewGuru/1 CFNetwork/1410.1 Darwin/22.6.0',
                    'accept-encoding': 'identity'
                },
                method='POST'
            )
            try:
                with urllib.request.urlopen(req, timeout=10) as resp:
                    resp_body = resp.read().decode()
                    print(f'[MGS] ✅ {resp.status} — body: [{resp_body}]')
                    LAST_MGS.update({'status': resp.status, 'ok': True, 'body': resp_body, 'url': url, 'afId': payload.get('events',[{}])[0].get('appsFlyerId','')})
                    self.send_json(200, {'status': resp.status, 'ok': True, 'body': resp_body})
            except urllib.error.HTTPError as e:
                body_err = e.read().decode()
                print(f'[MGS] ❌ {e.code} — {body_err}')
                self.send_json(200, {'status': e.code, 'ok': False, 'error': body_err})
            except Exception as ex:
                print(f'[MGS] ⚠️ {ex}')
                LAST_MGS.update({'status': 0, 'ok': False, 'error': str(ex), 'url': url})
                self.send_json(200, {'status': 0, 'ok': False, 'error': str(ex)})
        else:
            self.send_json(404, {'error': 'Not found'})

    def do_DELETE(self):
        p = urlparse(self.path).path
        u = self.get_user()
        if not u or u['role'] != 'admin': return self.send_json(403, {'error': 'Forbidden'})
        if p.startswith('/api/users/'):
            username = p.split('/')[-1]
            if username == 'admin': return self.send_json(400, {'error': 'Cannot delete admin'})
            users = load_json(USERS_FILE, [])
            users = [x for x in users if x['username'] != username]
            save_json(USERS_FILE, users)
            self.send_json(200, {'ok': True})
        else:
            self.send_json(404, {'error': 'Not found'})

if __name__ == '__main__':
    server = HTTPServer(('0.0.0.0', 8090), Handler)
    print('Allosh v2 running on port 8090')
    server.serve_forever()
