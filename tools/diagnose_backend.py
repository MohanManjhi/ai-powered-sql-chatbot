import socket
import urllib.request
import json
import sys

HOST = '127.0.0.1'
PORT = 5001
BASE = f'http://{HOST}:{PORT}'

print('TEST: socket connect to', HOST, PORT)
try:
    s = socket.create_connection((HOST, PORT), timeout=3)
    s.close()
    print('OK: socket connected')
except Exception as e:
    print('ERR: socket connect failed:', repr(e))

# GET /api/schema
print('\nTEST: GET /api/schema')
try:
    with urllib.request.urlopen(f'{BASE}/api/schema', timeout=5) as resp:
        print('STATUS', resp.getcode())
        ct = resp.headers.get('Content-Type')
        print('Content-Type:', ct)
        body = resp.read(1000).decode('utf-8', errors='replace')
        print('BODY snippet:\n', body[:1000].replace('\n','\\n'))
except Exception as e:
    print('ERR: GET /api/schema failed:', repr(e))

# POST /api/query
print('\nTEST: POST /api/query (SQL)')
post_data = json.dumps({'sql': 'SELECT 1', 'db_type': 'sql'}).encode('utf-8')
req = urllib.request.Request(f'{BASE}/api/query', data=post_data, headers={'Content-Type':'application/json'})
try:
    with urllib.request.urlopen(req, timeout=10) as resp:
        print('STATUS', resp.getcode())
        body = resp.read(2000).decode('utf-8', errors='replace')
        print('BODY snippet:\n', body[:2000].replace('\n','\\n'))
except Exception as e:
    print('ERR: POST /api/query failed:', repr(e))
    sys.exit(2)
