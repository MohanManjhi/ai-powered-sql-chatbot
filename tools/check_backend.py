import urllib.request, json, sys

url = 'http://localhost:5001/sql/execute'
payload = json.dumps({'query': 'SELECT 1'}).encode('utf-8')
req = urllib.request.Request(url, data=payload, headers={'Content-Type': 'application/json'})
try:
    with urllib.request.urlopen(req, timeout=5) as resp:
        print('STATUS', resp.getcode())
        print('BODY')
        print(resp.read().decode('utf-8'))
except Exception as e:
    print('ERROR', repr(e))
    sys.exit(2)
