-- PostgreSQL schema for the product data model (master doc section 7).
-- Every stored value carries an evidence label and a source, so the report can trace it.

CREATE TYPE evidence_label AS ENUM ('declared', 'derived', 'interpreted', 'verified', 'unknown');
CREATE TYPE food_category AS ENUM ('biscuits_cookies', 'breakfast_cereals', 'instant_noodles',
                                   'beverages', 'namkeen_chips');

CREATE TABLE products (
    product_id        BIGSERIAL PRIMARY KEY,
    name              TEXT,
    brand             TEXT,
    category          food_category,
    category_label    evidence_label NOT NULL DEFAULT 'unknown',
    variant           TEXT,
    gtin              TEXT,
    off_code          TEXT,                    -- matched Open Food Facts barcode, if any
    source_url        TEXT,
    collected_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    last_verified_at  TIMESTAMPTZ,
    conflict_flag     BOOLEAN NOT NULL DEFAULT FALSE,
    conflicts         JSONB NOT NULL DEFAULT '[]'
);

-- Price and pack size change over time: one row per observation (doc: time-stamp price).
CREATE TABLE price_observations (
    id            BIGSERIAL PRIMARY KEY,
    product_id    BIGINT NOT NULL REFERENCES products ON DELETE CASCADE,
    price_inr     NUMERIC(10, 2),
    pack_size     NUMERIC(10, 3),
    pack_unit     TEXT CHECK (pack_unit IN ('g', 'ml')),
    evidence      evidence_label NOT NULL,
    source        TEXT,
    observed_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- One row per nutrient. NULL value means unknown: never store 0 for a missing value.
CREATE TABLE nutrient_values (
    product_id    BIGINT NOT NULL REFERENCES products ON DELETE CASCADE,
    nutrient      TEXT NOT NULL CHECK (nutrient IN ('energy', 'protein', 'carbohydrate', 'total_sugars',
                       'added_sugars', 'total_fat', 'saturated_fat', 'trans_fat', 'fibre', 'sodium')),
    basis         TEXT NOT NULL CHECK (basis IN ('per_100g', 'per_100ml')),
    value         NUMERIC(10, 3),               -- kcal for energy, mg for sodium, g otherwise
    evidence      evidence_label NOT NULL,
    source        TEXT,
    note          TEXT,
    PRIMARY KEY (product_id, nutrient)
);

CREATE TABLE ingredients (
    product_id      BIGINT NOT NULL REFERENCES products ON DELETE CASCADE,
    ingredients_raw TEXT,
    normalised      JSONB NOT NULL DEFAULT '[]',
    additives_ins   TEXT[] NOT NULL DEFAULT '{}',
    allergens       TEXT[] NOT NULL DEFAULT '{}',
    evidence        evidence_label NOT NULL,
    source          TEXT,
    PRIMARY KEY (product_id)
);

CREATE TABLE claims (
    id            BIGSERIAL PRIMARY KEY,
    product_id    BIGINT NOT NULL REFERENCES products ON DELETE CASCADE,
    claim_id      TEXT NOT NULL,                -- fssai_claims.csv claim_id
    matched_text  TEXT NOT NULL,
    status        TEXT NOT NULL,                -- evidence status, not an accusation
    facts         JSONB NOT NULL DEFAULT '[]',
    rule          TEXT
);

-- Each analysis is stored with the methodology version that produced it.
CREATE TABLE analyses (
    id                    BIGSERIAL PRIMARY KEY,
    product_id            BIGINT NOT NULL REFERENCES products ON DELETE CASCADE,
    methodology_version   TEXT NOT NULL,
    nutrition             NUMERIC(5, 2),
    ingredients           NUMERIC(5, 2),
    transparency          NUMERIC(5, 2),
    claims                NUMERIC(5, 2),
    value                 NUMERIC(5, 2),
    overall               INTEGER,
    grade                 CHAR(1),
    report                JSONB NOT NULL,
    created_at            TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX ON products (category);
CREATE INDEX ON price_observations (product_id, observed_at DESC);
