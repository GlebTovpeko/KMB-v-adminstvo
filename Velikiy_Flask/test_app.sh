#!/bin/bash
URL="http://localhost" # Nginx слушает 80 порт
G='\033[0;32m'; R='\033[0;31m'; N='\033[0m'

pass() { echo -e "${G}✅ PASS:${N} $1"; }
fail() { echo -e "${R}❌ FAIL:${N} $1"; }

echo "🚀 Запуск тестов..."

# 1. GET All
curl -s $URL/users | grep -q "Alice" && pass "GET All" || fail "GET All"

# 2. POST
NAME="U_$(date +%s)"
RES=$(curl -s -X POST $URL/users -H "Content-Type: application/json" -d "{\"name\":\"$NAME\",\"email\":\"t@t.com\"}")
ID=$(echo $RES | grep -o '"id":[0-9]*' | cut -d: -f2)
[ -n "$ID" ] && pass "Create (ID: $ID)" || fail "Create"

# 3. GET One
curl -s $URL/users/$ID | grep -q "$NAME" && pass "Get One" || fail "Get One"

# 4. PUT
NEW="Upd_$NAME"
curl -s -X PUT $URL/users/$ID -H "Content-Type: application/json" -d "{\"name\":\"$NEW\"}" | grep -q "Updated" && pass "Update" || fail "Update"
sleep 6 
curl -s $URL/users/$ID | grep -q "$NEW" && pass "Verify Update" || fail "Verify Update"

# 5. Nginx Cache
H1=$(curl -sI $URL/users | grep X-Cache-Status)
H2=$(curl -sI $URL/users | grep X-Cache-Status)
echo "$H2" | grep -q "HIT" && pass "Nginx Cache ($H1 -> $H2)" || fail "Nginx Cache"

# 6. Invalidation
curl -s -X POST $URL/users -H "Content-Type: application/json" -d "{\"name\":\"NewGuy\",\"email\":\"n@n.com\"}" > /dev/null
sleep 6 
curl -s $URL/users | grep -q "NewGuy" && pass "Invalidation" || fail "Invalidation"

# 7. DELETE
curl -s -X DELETE $URL/users/$ID | grep -q "Deleted" && pass "Delete" || fail "Delete"
sleep 6 
[ $(curl -s -o /dev/null -w "%{http_code}" $URL/users/$ID) == "404" ] && pass "Verify Delete" || fail "Verify Delete"

echo "🏁 Done"