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

## Find duplicates

```sql
SELECT slug, COUNT(*)
FROM products
GROUP BY slug
HAVING COUNT(*) > 1;
```

## Fix duplicates (append -1, -2, etc.)

```sql
WITH duplicates AS (
    SELECT
        id,
        slug,
        ROW_NUMBER() OVER (PARTITION BY slug ORDER BY id) AS rn
    FROM products
)
UPDATE products p
SET slug = p.slug || '-' || d.rn
FROM duplicates d
WHERE p.id = d.id
  AND d.rn > 1;  -- only update the 2nd, 3rd, etc.

```
