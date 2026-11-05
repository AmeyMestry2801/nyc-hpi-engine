\timing on
CREATE INDEX IF NOT EXISTS idx_sales_boro_seg_date ON sales (borough, segment, sale_date);
CREATE INDEX IF NOT EXISTS idx_sales_property      ON sales (property_id);
CREATE INDEX IF NOT EXISTS idx_sales_bbl           ON sales (bbl);
CREATE INDEX IF NOT EXISTS idx_pairs_boro_seg_date ON repeat_pairs (borough, segment, date1);
CREATE INDEX IF NOT EXISTS idx_pairs_property      ON repeat_pairs (property_id);
ANALYZE;

SELECT segment, count(*) FROM sales GROUP BY segment ORDER BY segment;
SELECT geography, value FROM hpi_quarterly WHERE quarter = '2025Q4' ORDER BY geography;
SELECT indexname FROM pg_indexes WHERE schemaname = 'public' ORDER BY indexname;