#!/bin/bash
# Brand Brain API — Smoke Test Script
# Run after: docker compose -f infra/docker/compose.yml up -d --build
# And after: docker exec -it bb_api python -m app.scripts.seed

BASE="http://localhost/api"
echo "=== Brand Brain API Smoke Test ==="
echo ""

# 1. Health check
echo "1. Health check..."
curl -s $BASE/health | python3 -m json.tool
echo ""

# 2. Register a new user
echo "2. Register user..."
curl -s -X POST $BASE/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"test@test.com","password":"test123"}' | python3 -m json.tool
echo ""

# 3. Login
echo "3. Login..."
TOKEN=$(curl -s -X POST $BASE/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@brandbrain.dev","password":"admin123"}' | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")
echo "Token: ${TOKEN:0:20}..."
echo ""

# 4. Get current user
echo "4. Get /auth/me..."
curl -s $BASE/auth/me \
  -H "Authorization: Bearer $TOKEN" | python3 -m json.tool
echo ""

# 5. List organizations
echo "5. List organizations..."
curl -s "$BASE/orgs" \
  -H "Authorization: Bearer $TOKEN" | python3 -m json.tool
echo ""

# 6. Get org ID and list cost centers
ORG_ID=$(curl -s "$BASE/orgs" \
  -H "Authorization: Bearer $TOKEN" | python3 -c "import sys,json; data=json.load(sys.stdin); print(data[0]['id'] if data else '')")
echo "Org ID: $ORG_ID"

echo "6. List cost centers..."
curl -s "$BASE/cost-centers?org_id=$ORG_ID" \
  -H "Authorization: Bearer $TOKEN" | python3 -m json.tool
echo ""

# 7. List influencers
echo "7. List influencers..."
curl -s "$BASE/influencers?org_id=$ORG_ID" \
  -H "Authorization: Bearer $TOKEN" | python3 -m json.tool
echo ""

# 8. List content items
echo "8. List content items..."
curl -s "$BASE/content-items" \
  -H "Authorization: Bearer $TOKEN" | python3 -m json.tool
echo ""

# 9. List macro contents
echo "9. List macro contents..."
curl -s "$BASE/macro-contents?org_id=$ORG_ID" \
  -H "Authorization: Bearer $TOKEN" | python3 -m json.tool
echo ""

# 10. Test Marketing Agent
echo "10. Marketing Agent — generate_drafts..."
CC_ID=$(curl -s "$BASE/cost-centers?org_id=$ORG_ID" \
  -H "Authorization: Bearer $TOKEN" | python3 -c "import sys,json; data=json.load(sys.stdin); print(data[0]['id'] if data else '')")

curl -s -X POST "$BASE/agent/marketing/run" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{\"org_id\":\"$ORG_ID\",\"cc_id\":\"$CC_ID\",\"intent\":\"generate_drafts\",\"message\":\"mel natural e saúde\",\"channels\":[\"instagram\",\"linkedin\"]}" | python3 -m json.tool
echo ""

# 11. Test Market Agent
echo "11. Market Agent — run collection..."
curl -s -X POST "$BASE/agent/market/run" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{\"org_id\":\"$ORG_ID\",\"cc_id\":\"$CC_ID\",\"keywords\":[\"mel natural\",\"apicultura\",\"rastreabilidade\"]}" | python3 -m json.tool
echo ""

echo "=== Smoke test complete! ==="
echo "Open http://localhost/api/docs to see the full Swagger UI"
