CREATE ROLE nl_reader LOGIN PASSWORD 'readonly_local';
GRANT CONNECT ON DATABASE nyc_hpi TO nl_reader;
GRANT USAGE ON SCHEMA public TO nl_reader;
GRANT SELECT ON sales, repeat_pairs, hpi_quarterly TO nl_reader;
ALTER ROLE nl_reader SET statement_timeout = '10s';
ALTER ROLE nl_reader SET default_transaction_read_only = on;