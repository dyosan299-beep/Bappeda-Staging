# Auth Testing Playbook — Bappeda Kota Makassar

## Step 1: MongoDB
```
mongosh
use test_database
db.users.find({role: "admin"}).pretty()
```
Verify bcrypt hash starts with `$2b$`, index on users.email (unique).

## Step 2: API
```
curl -c cookies.txt -X POST http://localhost:8001/api/auth/login -H "Content-Type: application/json" -d '{"email":"admin@bappeda.makassarkota.go.id","password":"<TEST_ADMIN_PASSWORD>"}'
curl -b cookies.txt http://localhost:8001/api/auth/me
```
Login returns user object + sets access_token/refresh_token cookies. /me returns same user.
