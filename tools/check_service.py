import urllib.request, json, sys

BASE = 'http://localhost:5001'
paths = ['/', '/health']

for p in paths:
    url = BASE + p
    req = urllib.request.Request(url)
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            print('GET', p, 'STATUS', resp.getcode())
            ct = resp.headers.get('Content-Type')
            print('  Content-Type:', ct)
            body = resp.read(800).decode('utf-8', errors='replace')
            print('  BODY snippet:\n', body[:500].replace('\n','\\n'))
    except Exception as e:
        print('GET', p, 'ERROR', repr(e))

# POST test to /sql/execute
try:
    data = json.dumps({'query': 'SELECT 1'}).encode('utf-8')
    req = urllib.request.Request(BASE + '/sql/execute', data=data, headers={'Content-Type':'application/json'})
    with urllib.request.urlopen(req, timeout=5) as resp:
        print('POST /sql/execute STATUS', resp.getcode())
        ct = resp.headers.get('Content-Type')
        print('  Content-Type:', ct)
        body = resp.read(2000).decode('utf-8', errors='replace')
        print('  BODY snippet:\n', body[:1000].replace('\n','\\n'))
except Exception as e:
    print('POST /sql/execute ERROR', repr(e))
    sys.exit(2)
