CREATE TABLE IF NOT EXISTS products (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    barcode     TEXT UNIQUE NOT NULL,
    name        TEXT NOT NULL,
    price_buy   REAL NOT NULL DEFAULT 0,
    price_sell  REAL NOT NULL DEFAULT 0,
    stock       INTEGER NOT NULL DEFAULT 0,
    unit        TEXT NOT NULL DEFAULT 'pcs',
    created_at  TEXT NOT NULL DEFAULT (datetime('now','localtime')),
    updated_at  TEXT NOT NULL DEFAULT (datetime('now','localtime'))
);

CREATE TABLE IF NOT EXISTS transactions (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    date        TEXT NOT NULL DEFAULT (datetime('now','localtime')),
    subtotal    REAL NOT NULL DEFAULT 0,
    discount    REAL NOT NULL DEFAULT 0,
    total       REAL NOT NULL DEFAULT 0,
    payment     REAL NOT NULL DEFAULT 0,
    change      REAL NOT NULL DEFAULT 0,
    notes       TEXT
);

CREATE TABLE IF NOT EXISTS transaction_items (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    transaction_id  INTEGER NOT NULL REFERENCES transactions(id),
    product_id      INTEGER NOT NULL REFERENCES products(id),
    qty             INTEGER NOT NULL,
    price_sell      REAL NOT NULL,
    subtotal        REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS stock_in (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    date            TEXT NOT NULL DEFAULT (datetime('now','localtime')),
    supplier_name   TEXT,
    invoice_no      TEXT,
    notes           TEXT
);

CREATE TABLE IF NOT EXISTS stock_in_items (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    stock_in_id INTEGER NOT NULL REFERENCES stock_in(id),
    product_id  INTEGER NOT NULL REFERENCES products(id),
    qty         INTEGER NOT NULL,
    price_buy   REAL NOT NULL DEFAULT 0
);
