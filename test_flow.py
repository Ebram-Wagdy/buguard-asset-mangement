import requests
import uuid
import sys

# Base URL for the local API inside Docker
BASE_URL = "http://localhost:8000/api/v1"
TENANT_ID = "123e4567-e89b-12d3-a456-426614174000"
HEADERS = {"x-tenant-id": TENANT_ID}

def run_tests():
    print("Starting End-to-End Test Flow...\n")

    # 1. Test Ingestion (First Time)
    print("1. Testing POST /api/v1/assets/import (Initial Insert)")
    payload = [
        {"type": "domain", "value": "my-secret-server.com", "source": "manual", "tags": ["prod", "internal"]},
        {"type": "ip_address", "value": "192.168.1.50", "source": "manual", "tags": ["database"]}
    ]
    resp = requests.post(f"{BASE_URL}/assets/import", headers=HEADERS, json=payload)
    print(f"Status: {resp.status_code}")
    print(f"Response: {resp.text}\n")
    if resp.status_code != 200:
        sys.exit(1)

    # 2. Test Ingestion (Idempotent Update)
    print("2. Testing POST /api/v1/assets/import (Idempotent Update)")
    resp = requests.post(f"{BASE_URL}/assets/import", headers=HEADERS, json=payload)
    print(f"Status: {resp.status_code}")
    print(f"Response: {resp.text}\n")
    if resp.status_code != 200:
        sys.exit(1)

    # 3. Test AI Query
    print("3. Testing POST /api/v1/ai/query")
    resp = requests.post(f"{BASE_URL}/ai/query", headers=HEADERS, json={"query": "What domains do I own?"})
    print(f"Status: {resp.status_code}")
    print(f"Response: {resp.text}\n")
    if resp.status_code != 200:
        sys.exit(1)

    # We need an asset ID to test scoring and enrichment.
    from sqlalchemy import create_engine, text
    from sqlalchemy.orm import sessionmaker
    engine = create_engine("postgresql://postgres:postgres@db:5432/darkatlas")
    Session = sessionmaker(bind=engine)
    session = Session()
    res = session.execute(text("SELECT id FROM assets WHERE tenant_id = '123e4567-e89b-12d3-a456-426614174000' LIMIT 1"))
    asset_id = str(res.fetchone()[0])
    session.close()

    print(f"Grabbed Asset ID for next tests: {asset_id}\n")

    # 4. Test AI Scoring
    print(f"4. Testing POST /api/v1/ai/score/{asset_id}")
    resp = requests.post(f"{BASE_URL}/ai/score/{asset_id}", headers=HEADERS)
    print(f"Status: {resp.status_code}")
    print(f"Response: {resp.text}\n")
    if resp.status_code != 200:
        sys.exit(1)

    # 5. Test AI Enrichment
    print(f"5. Testing POST /api/v1/ai/enrich/{asset_id}")
    resp = requests.post(f"{BASE_URL}/ai/enrich/{asset_id}", headers=HEADERS)
    print(f"Status: {resp.status_code}")
    print(f"Response: {resp.text}\n")
    if resp.status_code != 200:
        sys.exit(1)

    # 6. Test AI Report Generation
    print("6. Testing GET /api/v1/ai/report/generate")
    resp = requests.get(f"{BASE_URL}/ai/report/generate", headers=HEADERS)
    print(f"Status: {resp.status_code}")
    print(f"Response: {resp.text[:200]}...\n")
    if resp.status_code != 200:
        sys.exit(1)

    print("ALL TESTS PASSED PERFECTLY!")

if __name__ == "__main__":
    run_tests()
