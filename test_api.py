from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

r = client.get('/devices?month=2025-09')
print('status', r.status_code)
print(r.json()[:10])

r2 = client.get('/availability/10243?month=2025-09&prorate=true')
print('avail status', r2.status_code)
print(r2.json())
