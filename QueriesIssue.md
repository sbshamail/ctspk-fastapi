# SQL Queries Issue Solving

## Since you manually inserted rows with explicit id values, Postgres’ sequence counter didn’t advance.

### So now, when you insert a new row without specifying id, it still tries to use an old number (like 8), causing the conflict.

```sql
-- # -- Adjust the sequence to the correct next value
SELECT setval(
  pg_get_serial_sequence('categories', 'id'),
  COALESCE((SELECT MAX(id) FROM categories), 1) + 1,
  false
);
```
