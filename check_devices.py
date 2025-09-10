import urllib.request
url = 'http://127.0.0.1:8000/devices?month=2025-09'
with urllib.request.urlopen(url, timeout=10) as r:
	body = r.read().decode('utf-8')
	print(r.status)
	print(body[:1000])
