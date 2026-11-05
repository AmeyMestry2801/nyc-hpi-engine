\pset pager off
\timing on

-- A. How concentrated are the pairs? (a property with 9+ pairs in 22 years is suspicious)
WITH c AS (SELECT property_id, count(*) AS n FROM repeat_pairs GROUP BY property_id)
SELECT CASE WHEN n <= 3 THEN '1-3' WHEN n <= 8 THEN '4-8' WHEN n <= 20 THEN '9-20' ELSE '21+' END AS pairs_per_property,
       count(*) AS properties, sum(n) AS pairs
FROM c GROUP BY 1 ORDER BY min(n);

-- B. The biggest groups (the property_id is "borough|zip|house|unit|street")
SELECT property_id, segment, count(*) AS pairs, min(date0) AS first_sale, max(date1) AS last_sale
FROM repeat_pairs GROUP BY property_id, segment ORDER BY pairs DESC LIMIT 15;

-- C. Label-like units that still sit in the condo/co-op pairs (3+ leading letters)
SELECT split_part(property_id, '|', 4) AS unit, count(*) AS pairs
FROM repeat_pairs
WHERE segment = 'CONDO_COOP' AND split_part(property_id, '|', 4) ~ '^[A-Z]{3,}'
GROUP BY 1 ORDER BY pairs DESC LIMIT 25;