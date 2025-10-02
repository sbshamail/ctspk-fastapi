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

## Categories

```sql
-- if column not found
ALTER TABLE categories
ADD COLUMN root_id INT;
-- 1. Set root_id for top-level categories
UPDATE categories
SET root_id = id
WHERE parent_id IS NULL;

-- 2. Recursively update all child and subchild categories
WITH RECURSIVE category_hierarchy AS (
    SELECT id, parent_id, id AS root_id
    FROM categories
    WHERE parent_id IS NULL  -- top-level categories

    UNION ALL

    SELECT c.id, c.parent_id, ch.root_id
    FROM categories c
    JOIN category_hierarchy ch ON c.parent_id = ch.id
)
UPDATE categories c
SET root_id = ch.root_id
FROM category_hierarchy ch
WHERE c.id = ch.id;
```
