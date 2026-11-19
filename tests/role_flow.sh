#!/bin/bash
# Uji cepat alur role: operator -> petugas -> verval. Pakai cookie jar per peran.
B=http://localhost:8001/api
J=/tmp/jar
login() { curl -s -c $J.$1 -H 'Content-Type: application/json' -d "{\"email\":\"$2\",\"password\":\"$3\"}" $B/auth/login; echo; }
echo "== login operator"; login op operator.rappocini@makassarkota.go.id Operator2026
echo "== login superadmin"; login sa admin@bappeda.makassarkota.go.id AdminBappeda2026
echo "== superadmin coba buat petugas (harus 403)"
curl -s -b $J.sa -H 'Content-Type: application/json' -d '{"email":"petugas.x@test.id","password":"Petugas123","name":"X","role":"petugas","wilayah":"Rappocini"}' $B/admin/users; echo
echo "== operator kelurahan options"; curl -s -b $J.op $B/admin/users/kelurahan | head -c 200; echo
echo "== operator buat petugas tanpa kelurahan (harus 422)"
curl -s -b $J.op -H 'Content-Type: application/json' -d '{"email":"petugas.gs@test.id","password":"Petugas123","name":"Petugas GS RW1"}' $B/admin/users; echo
echo "== operator buat petugas Gunung Sari RW 1 RT 1,2"
curl -s -b $J.op -H 'Content-Type: application/json' -d '{"email":"petugas.gs@test.id","password":"Petugas123","name":"Petugas GS RW1","kelurahan":"Gunung Sari","rw":"01","rt":["001","2"]}' $B/admin/users; echo
echo "== operator buat verifikator (harus 403)"
curl -s -b $J.op -H 'Content-Type: application/json' -d '{"email":"v@test.id","password":"Petugas123","name":"V","role":"verifikator"}' $B/admin/users; echo
echo "== operator list users"; curl -s -b $J.op $B/admin/users | python3 -c "import sys,json; [print(u['email'],u['role'],u['wilayah'],u.get('kelurahan'),u.get('rw'),u.get('rt')) for u in json.load(sys.stdin)]"
echo "== login petugas"; login pt petugas.gs@test.id Petugas123
echo "== petugas /verval/saya"; curl -s -b $J.pt $B/verval/saya | head -c 500; echo
echo "== petugas /verval/sasaran"; curl -s -b $J.pt $B/verval/sasaran | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['total']); [print(i['kepala_keluarga'],i['kelurahan'],i['rw'],i['rt'],i['dasar_akses']) for i in d['items']]"
echo "== petugas akses /admin/users (harus 403)"; curl -s -b $J.pt $B/admin/users; echo
echo "== petugas akses /sosial/households (dibatasi)"; curl -s -b $J.pt "$B/sosial/households?size=5" | head -c 300; echo
echo "== petugas /regions (hanya Rappocini)"; curl -s -b $J.pt $B/regions | python3 -c "import sys,json; print([r['nama'] for r in json.load(sys.stdin)])"
echo "== operator /regions"; curl -s -b $J.op $B/regions | python3 -c "import sys,json; print([r['nama'] for r in json.load(sys.stdin)])"
echo "== operator /kelurahan?kecamatan=Tallo (dipaksa Rappocini)"; curl -s -b $J.op "$B/kelurahan?kecamatan=Tallo" | python3 -c "import sys,json; print(sorted({k['kecamatan'] for k in json.load(sys.stdin)}))"
echo "== superadmin /regions (semua)"; curl -s -b $J.sa $B/regions | python3 -c "import sys,json; print(len(json.load(sys.stdin)))"
