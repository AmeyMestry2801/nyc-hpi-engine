\timing on
SET statement_timeout = '30s';

-- 1. Typical prices by borough and segment, 2024 (median needs an ordered-set aggregate)
SELECT borough, segment, count(*) AS sales,
       round(avg(sale_price)) AS avg_price,
       round((percentile_cont(0.5) WITHIN GROUP (ORDER BY sale_price))::numeric) AS median_price
FROM sales
WHERE sale_date >= '2024-01-01' AND sale_date < '2025-01-01'
GROUP BY borough, segment
ORDER BY borough, segment;

-- 2. Most frequently sold properties, with first and last price
--    (count first, keep 10, then look up prices through the property_id index)
WITH top AS (
    SELECT property_id, count(*) AS n_sales
    FROM sales
    GROUP BY property_id
    ORDER BY n_sales DESC
    LIMIT 10
)
SELECT t.n_sales, max(s.address) AS address,
       (array_agg(s.sale_price ORDER BY s.sale_date))[1]      AS first_price,
       (array_agg(s.sale_price ORDER BY s.sale_date DESC))[1] AS last_price
FROM top t
JOIN sales s USING (property_id)
GROUP BY t.property_id, t.n_sales
ORDER BY t.n_sales DESC;

-- 3. Quick flips: resold within 90-180 days for more than 30% gain (pairs are at least 90 days apart)
WITH flips AS (
    SELECT property_id, date0, price0, date1, price1,
           round(100 * (price1 / price0 - 1), 1) AS pct_gain
    FROM repeat_pairs
    WHERE days <= 180 AND price0 >= 200000 AND price1 > 1.3 * price0
    ORDER BY pct_gain DESC
    LIMIT 15
)
SELECT a.address, f.date0, f.price0, f.date1, f.price1, f.pct_gain
FROM flips f
CROSS JOIN LATERAL (SELECT address FROM sales s WHERE s.property_id = f.property_id LIMIT 1) a
ORDER BY f.pct_gain DESC;

-- 4. Median annualized appreciation from repeat sales, 2015 onward
SELECT borough, segment, count(*) AS pairs,
       round((percentile_cont(0.5) WITHIN GROUP (ORDER BY exp(log_ratio * 365.25 / days) - 1) * 100)::numeric, 2)
           AS median_annual_pct
FROM repeat_pairs
WHERE date1 >= '2015-01-01'
GROUP BY borough, segment
ORDER BY borough, segment;

-- 5. Citywide index, year-over-year change (LAG by 4 quarters)
SELECT quarter, value,
       round(100 * (value / LAG(value, 4) OVER (ORDER BY quarter_start) - 1), 1) AS yoy_pct
FROM hpi_quarterly
WHERE geography = 'City'
ORDER BY quarter_start DESC
LIMIT 8;

-- 6. Worst peak-to-trough drop during the 2003-2012 cycle, per geography (running max window)
WITH x AS (
    SELECT geography, value,
           max(value) OVER (PARTITION BY geography ORDER BY quarter_start) AS running_peak
    FROM hpi_quarterly
    WHERE quarter_start < '2013-01-01'
)
SELECT geography, round(min(100 * (value / running_peak - 1)), 1) AS max_drawdown_pct
FROM x
GROUP BY geography
ORDER BY max_drawdown_pct;