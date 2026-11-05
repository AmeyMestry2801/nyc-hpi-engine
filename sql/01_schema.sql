CREATE TABLE sales (
    sale_id           BIGINT PRIMARY KEY,
    property_id       TEXT NOT NULL,          -- entity-resolution group (Phase 2)
    borough           SMALLINT NOT NULL,      -- 1 Manhattan, 2 Bronx, 3 Brooklyn, 4 Queens, 5 Staten Island
    neighborhood      TEXT,
    segment           TEXT NOT NULL,          -- HOUSE, CONDO_COOP, MULTIFAMILY
    building_class    TEXT,
    address           TEXT,
    unit              TEXT,
    zip_code          INTEGER,
    block             INTEGER,
    lot               INTEGER,
    bbl               BIGINT,
    residential_units INTEGER,
    total_units       INTEGER,
    land_sqft         NUMERIC,
    gross_sqft        NUMERIC,
    year_built        INTEGER,
    sale_date         DATE NOT NULL,
    sale_price        NUMERIC(14,2) NOT NULL
);

CREATE TABLE repeat_pairs (
    pair_id      BIGSERIAL PRIMARY KEY,
    property_id  TEXT NOT NULL,
    segment      TEXT NOT NULL,
    borough      SMALLINT NOT NULL,
    neighborhood TEXT,
    bbl          BIGINT,
    date0        DATE NOT NULL,
    price0       NUMERIC(14,2) NOT NULL,
    date1        DATE NOT NULL,
    price1       NUMERIC(14,2) NOT NULL,
    days         INTEGER NOT NULL,
    log_ratio    DOUBLE PRECISION NOT NULL
);

CREATE TABLE hpi_quarterly (
    quarter       TEXT NOT NULL,        -- e.g. 2019Q4
    quarter_start DATE NOT NULL,
    geography     TEXT NOT NULL,        -- City, HOUSE, CONDO_COOP, MULTIFAMILY, Manhattan, Bronx, ...
    geo_type      TEXT NOT NULL,        -- city, segment, borough
    value         NUMERIC(8,2) NOT NULL, -- index level, 2004Q1 = 100
    PRIMARY KEY (quarter, geography)
);