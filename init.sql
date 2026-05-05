
CREATE TABLE users (
    id BIGINT NOT NULL,
    username VARCHAR(255),
    phone VARCHAR(20),
    full_name VARCHAR(255),
    join_date TIMESTAMP DEFAULT NOW(),
    is_banned BOOLEAN DEFAULT FALSE,
    type VARCHAR(20) CHECK (type IN ('tenant', 'owner', 'realtor')) NOT NULL
);

CREATE TABLE listings (
    id SERIAL PRIMARY KEY,
    owner_id BIGINT NOT NULL REFERENCES users(id),
    status VARCHAR(20) DEFAULT 'available' 
        CHECK (status IN ('available', 'taken', 'disabled', 'pending', 'rejected')),  -- pending = awaiting moderation
    
    -- location
    lon DECIMAL(9,6),
    lat DECIMAL(8,6),
    address VARCHAR(255),
    district VARCHAR(100),  -- Chilonzor, Yunusobod etc — useful for filtering without GPS
    
    -- property details
    price INT,
    price_negotiable BOOLEAN DEFAULT FALSE,
    currency VARCHAR(3) DEFAULT 'USD',  -- some list in UZS
    rooms INT,
    floor INT,
    total_floors INT,
    area_sqm DECIMAL(6,2),  -- square meters
    
    -- tenant preferences
    for_boys BOOLEAN DEFAULT FALSE,
    for_girls BOOLEAN DEFAULT FALSE,
    for_families BOOLEAN DEFAULT FALSE,
    max_tenants INT,
    needed_tenants INT,
    
    -- utilities
    utils_included BOOLEAN DEFAULT FALSE,
    
    -- amenities (see below)
    has_wifi BOOLEAN DEFAULT FALSE,
    has_washing_machine BOOLEAN DEFAULT FALSE,
    has_fridge BOOLEAN DEFAULT FALSE,
    has_ac BOOLEAN DEFAULT FALSE,
    has_heating BOOLEAN DEFAULT FALSE,
    has_parking BOOLEAN DEFAULT FALSE,
    has_elevator BOOLEAN DEFAULT FALSE,
    has_furniture BOOLEAN DEFAULT FALSE,
    
    description TEXT,  -- free text for anything else
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);


CREATE TABLE listing_photos (
    id SERIAL PRIMARY KEY,
    listing_id INT REFERENCES listings(id) ON DELETE CASCADE,
    telegram_file_id TEXT NOT NULL,  -- store this, retrieve image anytime
    order_index INT DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW()
);