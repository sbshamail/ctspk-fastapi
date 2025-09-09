```bash
docker compose -f mysql-compose.yml up -d
docker exec -it mysql8_ctspk mysql -u root -p
#Connect from host (your Ubuntu)
mysql -h 127.0.0.1 -P 3306 -u root -p

```
