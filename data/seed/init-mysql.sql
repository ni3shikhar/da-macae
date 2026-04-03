-- =============================================================================
-- DA-MACAÉ :: MySQL Source Database Seed Data
-- =============================================================================
-- Creates sample tables with MySQL-specific data types for data mapping tests
-- =============================================================================

-- Use the source database
USE source_db;

-- Drop existing tables if they exist (in dependency order)
DROP TABLE IF EXISTS payment_transactions;
DROP TABLE IF EXISTS inventory_movements;
DROP TABLE IF EXISTS inventory;
DROP TABLE IF EXISTS suppliers;
DROP TABLE IF EXISTS product_reviews;
DROP TABLE IF EXISTS products;
DROP TABLE IF EXISTS product_categories;
DROP TABLE IF EXISTS user_sessions;
DROP TABLE IF EXISTS users;

-- =============================================================================
-- Table: users
-- Tests: AUTO_INCREMENT, ENUM, SET, TIMESTAMP, JSON
-- =============================================================================
CREATE TABLE users (
    user_id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) NOT NULL UNIQUE,
    email VARCHAR(150) NOT NULL UNIQUE,
    password_hash CHAR(60) NOT NULL,
    first_name VARCHAR(50),
    last_name VARCHAR(50),
    display_name VARCHAR(100) GENERATED ALWAYS AS (CONCAT(COALESCE(first_name, ''), ' ', COALESCE(last_name, ''))) STORED,
    user_role ENUM('admin', 'manager', 'staff', 'customer') NOT NULL DEFAULT 'customer',
    permissions SET('read', 'write', 'delete', 'admin') DEFAULT 'read',
    phone VARCHAR(20),
    avatar_url VARCHAR(500),
    preferences JSON,
    is_verified TINYINT(1) DEFAULT 0,
    is_active TINYINT(1) DEFAULT 1,
    failed_login_attempts TINYINT UNSIGNED DEFAULT 0,
    last_login DATETIME,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_email (email),
    INDEX idx_role (user_role)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

INSERT INTO users (username, email, password_hash, first_name, last_name, user_role, permissions, phone, preferences, is_verified, last_login) VALUES
('admin', 'admin@company.com', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/X4', 'Admin', 'User', 'admin', 'read,write,delete,admin', '+1-555-0001', '{"theme": "dark", "notifications": true, "language": "en"}', 1, '2024-02-20 10:30:00'),
('jmanager', 'jane.manager@company.com', '$2b$12$abc123def456', 'Jane', 'Manager', 'manager', 'read,write,delete', '+1-555-0002', '{"theme": "light", "notifications": true}', 1, '2024-02-19 15:45:00'),
('bstaff', 'bob.staff@company.com', '$2b$12$xyz789', 'Bob', 'Staff', 'staff', 'read,write', '+1-555-0003', NULL, 1, '2024-02-18 09:00:00'),
('customer1', 'alice@email.com', '$2b$12$cust1hash', 'Alice', 'Customer', 'customer', 'read', NULL, '{"newsletter": true}', 1, '2024-02-15 11:20:00'),
('customer2', 'charlie@email.com', '$2b$12$cust2hash', 'Charlie', 'Brown', 'customer', 'read', '+1-555-0005', NULL, 0, NULL),
('customer3', 'diana@email.com', '$2b$12$cust3hash', 'Diana', 'Prince', 'customer', 'read,write', '+1-555-0006', '{"theme": "auto"}', 1, '2024-02-10 16:30:00');

-- =============================================================================
-- Table: user_sessions
-- Tests: BINARY/VARBINARY, DATETIME vs TIMESTAMP, IPV6 support
-- =============================================================================
CREATE TABLE user_sessions (
    session_id BINARY(16) PRIMARY KEY,
    user_id INT NOT NULL,
    session_token VARCHAR(255) NOT NULL,
    ip_address VARCHAR(45),  -- Supports IPv6
    user_agent TEXT,
    device_fingerprint VARBINARY(32),
    started_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    expires_at DATETIME NOT NULL,
    last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    is_active TINYINT(1) DEFAULT 1,
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
) ENGINE=InnoDB;

INSERT INTO user_sessions (session_id, user_id, session_token, ip_address, user_agent, started_at, expires_at) VALUES
(UNHEX('550e8400e29b41d4a716446655440001'), 1, 'tok_admin_abc123', '192.168.1.100', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0', '2024-02-20 10:30:00', '2024-02-21 10:30:00'),
(UNHEX('550e8400e29b41d4a716446655440002'), 2, 'tok_jane_def456', '10.0.0.50', 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15) Safari/17.0', '2024-02-19 15:45:00', '2024-02-20 15:45:00'),
(UNHEX('550e8400e29b41d4a716446655440003'), 4, 'tok_alice_ghi789', '2001:db8:85a3::8a2e:370:7334', 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0)', '2024-02-15 11:20:00', '2024-02-16 11:20:00');

-- =============================================================================
-- Table: product_categories
-- Tests: HIERARCHICAL WITH PATH, TEXT COLUMNS
-- =============================================================================
CREATE TABLE product_categories (
    category_id INT AUTO_INCREMENT PRIMARY KEY,
    category_name VARCHAR(100) NOT NULL,
    category_slug VARCHAR(100) NOT NULL UNIQUE,
    parent_id INT,
    category_path VARCHAR(500),  -- Materialized path for hierarchy
    description TEXT,
    meta_keywords VARCHAR(255),
    meta_description VARCHAR(500),
    image_url VARCHAR(500),
    display_order SMALLINT DEFAULT 0,
    is_visible TINYINT(1) DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (parent_id) REFERENCES product_categories(category_id) ON DELETE SET NULL,
    INDEX idx_parent (parent_id),
    INDEX idx_slug (category_slug)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

INSERT INTO product_categories (category_name, category_slug, parent_id, category_path, description, display_order) VALUES
('Clothing', 'clothing', NULL, '/clothing', 'All types of clothing and apparel', 1),
('Men''s Wear', 'mens-wear', 1, '/clothing/mens-wear', 'Men''s clothing and accessories', 1),
('Women''s Wear', 'womens-wear', 1, '/clothing/womens-wear', 'Women''s clothing and accessories', 2),
('Shirts', 'shirts', 2, '/clothing/mens-wear/shirts', 'Men''s shirts - casual and formal', 1),
('Pants', 'pants', 2, '/clothing/mens-wear/pants', 'Men''s pants and trousers', 2),
('Dresses', 'dresses', 3, '/clothing/womens-wear/dresses', 'Women''s dresses for all occasions', 1),
('Accessories', 'accessories', NULL, '/accessories', 'Fashion accessories', 2),
('Watches', 'watches', 7, '/accessories/watches', 'Wristwatches and smart watches', 1);

-- =============================================================================
-- Table: products
-- Tests: DECIMAL PRECISION, DOUBLE, MEDIUMTEXT, JSON, FULLTEXT INDEX
-- =============================================================================
CREATE TABLE products (
    product_id INT AUTO_INCREMENT PRIMARY KEY,
    sku VARCHAR(50) NOT NULL UNIQUE,
    product_name VARCHAR(200) NOT NULL,
    short_description VARCHAR(500),
    full_description MEDIUMTEXT,
    category_id INT NOT NULL,
    brand VARCHAR(100),
    price DECIMAL(10,2) NOT NULL,
    compare_at_price DECIMAL(10,2),
    cost DECIMAL(10,2),
    weight_grams INT UNSIGNED,
    dimensions JSON,  -- {"length": 10, "width": 5, "height": 2}
    color VARCHAR(50),
    size VARCHAR(20),
    material VARCHAR(100),
    tags JSON,  -- ["summer", "casual", "sale"]
    inventory_quantity INT DEFAULT 0,
    low_stock_threshold INT DEFAULT 5,
    allow_backorder TINYINT(1) DEFAULT 0,
    rating_avg DOUBLE(3,2) DEFAULT 0.00,
    rating_count INT UNSIGNED DEFAULT 0,
    view_count INT UNSIGNED DEFAULT 0,
    status ENUM('draft', 'active', 'archived') DEFAULT 'draft',
    published_at DATETIME,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (category_id) REFERENCES product_categories(category_id),
    INDEX idx_category (category_id),
    INDEX idx_status (status),
    INDEX idx_price (price),
    FULLTEXT idx_search (product_name, short_description)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

INSERT INTO products (sku, product_name, short_description, full_description, category_id, brand, price, compare_at_price, cost, weight_grams, dimensions, color, size, material, tags, inventory_quantity, rating_avg, rating_count, status, published_at) VALUES
('SHIRT-OXF-BLU-M', 'Oxford Button-Down Shirt', 'Classic oxford shirt in navy blue', 'Premium quality oxford cloth button-down shirt. Perfect for business casual or smart casual occasions. Features a comfortable regular fit with a button-down collar.', 4, 'ClassicWear', 59.99, 79.99, 25.00, 280, '{"length": 75, "width": 55, "height": 2}', 'Navy Blue', 'M', '100% Cotton', '["business", "casual", "classic"]', 150, 4.50, 45, 'active', '2024-01-01 00:00:00'),
('SHIRT-OXF-WHT-L', 'Oxford Button-Down Shirt', 'Classic oxford shirt in white', 'Premium quality oxford cloth button-down shirt. Perfect for business casual or smart casual occasions.', 4, 'ClassicWear', 59.99, 79.99, 25.00, 290, '{"length": 78, "width": 58, "height": 2}', 'White', 'L', '100% Cotton', '["business", "casual", "classic"]', 200, 4.60, 62, 'active', '2024-01-01 00:00:00'),
('PANTS-CHI-KHK-32', 'Classic Chino Pants', 'Comfortable chino pants in khaki', 'Versatile chino pants made from stretch cotton twill. Features a modern slim fit with a comfortable stretch.', 5, 'UrbanFit', 69.99, NULL, 30.00, 450, '{"waist": 32, "length": 32, "inseam": 30}', 'Khaki', '32x32', '98% Cotton 2% Elastane', '["casual", "workwear"]', 80, 4.20, 28, 'active', '2024-01-15 00:00:00'),
('DRESS-FLR-RED-S', 'Floral Summer Dress', 'Beautiful floral print summer dress', 'Lightweight summer dress with a gorgeous floral print. Features a flattering A-line silhouette and adjustable straps.', 6, 'BellaStyle', 89.99, 119.99, 35.00, 320, '{"length": 95, "bust": 85, "waist": 68}', 'Red Floral', 'S', 'Viscose Blend', '["summer", "floral", "sale"]', 45, 4.80, 89, 'active', '2024-02-01 00:00:00'),
('WATCH-SMT-BLK', 'Smart Fitness Watch', 'Advanced fitness tracking smartwatch', 'Feature-packed smartwatch with heart rate monitoring, GPS, and 7-day battery life. Water resistant to 50m.', 8, 'TechTime', 199.99, 249.99, 85.00, 45, '{"diameter": 44, "thickness": 11}', 'Black', 'One Size', 'Aluminum/Silicone', '["fitness", "smart", "tech"]', 120, 4.40, 156, 'active', '2024-01-20 00:00:00'),
('SHIRT-POLO-GRN-XL', 'Premium Polo Shirt', 'Soft cotton polo in forest green', 'Classic polo shirt made from pique cotton. Ribbed collar and cuffs with two-button placket.', 4, 'SportStyle', 44.99, NULL, 18.00, 250, '{"length": 76, "chest": 62}', 'Forest Green', 'XL', 'Cotton Pique', '["casual", "sport"]', 0, 4.10, 15, 'active', '2024-02-10 00:00:00'),
('DRESS-EVE-BLK-M', 'Elegant Evening Dress', 'Stunning black evening dress', 'Sophisticated evening dress perfect for formal occasions. Features a sleek silhouette with subtle shimmer.', 6, 'Elegance', 159.99, NULL, 65.00, 480, '{"length": 145, "bust": 90, "waist": 72}', 'Black', 'M', 'Polyester Blend', '["formal", "evening", "elegant"]', 25, 4.90, 42, 'draft', NULL);

-- =============================================================================
-- Table: product_reviews
-- Tests: FOREIGN KEYS, TIMESTAMPS, BOOLEAN PATTERN
-- =============================================================================
CREATE TABLE product_reviews (
    review_id INT AUTO_INCREMENT PRIMARY KEY,
    product_id INT NOT NULL,
    user_id INT NOT NULL,
    rating TINYINT UNSIGNED NOT NULL CHECK (rating BETWEEN 1 AND 5),
    title VARCHAR(200),
    review_text TEXT,
    pros TEXT,
    cons TEXT,
    is_verified_purchase TINYINT(1) DEFAULT 0,
    helpful_votes INT UNSIGNED DEFAULT 0,
    unhelpful_votes INT UNSIGNED DEFAULT 0,
    is_featured TINYINT(1) DEFAULT 0,
    status ENUM('pending', 'approved', 'rejected') DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (product_id) REFERENCES products(product_id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users(user_id),
    INDEX idx_product (product_id),
    INDEX idx_user (user_id),
    INDEX idx_rating (rating)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

INSERT INTO product_reviews (product_id, user_id, rating, title, review_text, pros, cons, is_verified_purchase, helpful_votes, status) VALUES
(1, 4, 5, 'Perfect fit and quality!', 'This shirt exceeded my expectations. The fabric is soft yet durable, and the fit is exactly as described. Great for both work and casual wear.', 'Soft fabric, true to size, versatile', 'None so far', 1, 12, 'approved'),
(1, 6, 4, 'Good shirt, minor issue', 'Overall a great shirt. The color is slightly darker than shown in photos but still looks good.', 'Quality construction, comfortable', 'Color slightly different from photos', 1, 8, 'approved'),
(3, 4, 4, 'Comfortable everyday pants', 'These chinos are my new go-to pants. Very comfortable with just the right amount of stretch.', 'Comfortable, good stretch, nice color', 'Could be slightly longer', 1, 5, 'approved'),
(4, 6, 5, 'Gorgeous dress!', 'Absolutely love this dress! The print is beautiful and the fit is flattering. Got so many compliments!', 'Beautiful print, flattering fit, light fabric', NULL, 1, 22, 'approved'),
(5, 4, 4, 'Great features for the price', 'This smartwatch has everything I need for tracking my workouts. Battery life is impressive.', 'Long battery, accurate tracking, waterproof', 'App could be better', 1, 18, 'approved');

-- =============================================================================
-- Table: suppliers
-- Tests: MULTIPLE ADDRESS FIELDS, CONTACT INFO, STATUS
-- =============================================================================
CREATE TABLE suppliers (
    supplier_id INT AUTO_INCREMENT PRIMARY KEY,
    supplier_code VARCHAR(20) NOT NULL UNIQUE,
    company_name VARCHAR(150) NOT NULL,
    contact_person VARCHAR(100),
    email VARCHAR(150),
    phone VARCHAR(30),
    fax VARCHAR(30),
    website VARCHAR(255),
    address_line1 VARCHAR(200),
    address_line2 VARCHAR(200),
    city VARCHAR(100),
    state_province VARCHAR(100),
    postal_code VARCHAR(20),
    country VARCHAR(50) DEFAULT 'USA',
    tax_id VARCHAR(50),
    payment_terms VARCHAR(50) DEFAULT 'Net 30',
    credit_limit DECIMAL(12,2),
    current_balance DECIMAL(12,2) DEFAULT 0.00,
    rating TINYINT UNSIGNED CHECK (rating BETWEEN 1 AND 5),
    notes TEXT,
    is_active TINYINT(1) DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

INSERT INTO suppliers (supplier_code, company_name, contact_person, email, phone, website, address_line1, city, state_province, postal_code, country, payment_terms, credit_limit, rating) VALUES
('SUP-001', 'Fashion Fabrics Inc', 'Maria Garcia', 'mgarcia@fashionfabrics.com', '+1-555-2001', 'www.fashionfabrics.com', '100 Textile Way', 'Los Angeles', 'CA', '90001', 'USA', 'Net 30', 100000.00, 5),
('SUP-002', 'Global Garments Ltd', 'James Chen', 'jchen@globalgarments.com', '+86-21-5555-1234', 'www.globalgarments.cn', '888 Manufacturing Blvd', 'Shanghai', 'Shanghai', '200001', 'China', 'Net 45', 250000.00, 4),
('SUP-003', 'TechWear Supplies', 'Anna Smith', 'asmith@techwear.com', '+1-555-2003', 'www.techwearsupplies.com', '500 Innovation Dr', 'San Jose', 'CA', '95110', 'USA', 'Net 30', 75000.00, 4),
('SUP-004', 'EuroStyle Imports', 'Paolo Rossi', 'prossi@eurostyle.eu', '+39-02-5555-6789', 'www.eurostyle-imports.eu', 'Via della Moda 25', 'Milan', 'Lombardy', '20121', 'Italy', 'Net 60', 150000.00, 5);

-- =============================================================================
-- Table: inventory
-- Tests: COMPOSITE UNIQUE, LOCATION TRACKING
-- =============================================================================
CREATE TABLE inventory (
    inventory_id INT AUTO_INCREMENT PRIMARY KEY,
    product_id INT NOT NULL,
    warehouse_code VARCHAR(10) NOT NULL,
    location_bin VARCHAR(20),
    quantity_on_hand INT NOT NULL DEFAULT 0,
    quantity_reserved INT DEFAULT 0,
    quantity_available INT GENERATED ALWAYS AS (quantity_on_hand - quantity_reserved) STORED,
    reorder_point INT DEFAULT 10,
    reorder_quantity INT DEFAULT 50,
    last_counted_at DATETIME,
    last_received_at DATETIME,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (product_id) REFERENCES products(product_id) ON DELETE CASCADE,
    UNIQUE KEY uk_product_warehouse (product_id, warehouse_code),
    INDEX idx_warehouse (warehouse_code)
) ENGINE=InnoDB;

INSERT INTO inventory (product_id, warehouse_code, location_bin, quantity_on_hand, quantity_reserved, reorder_point, last_counted_at) VALUES
(1, 'WH-EAST', 'A-01-01', 100, 5, 20, '2024-02-15 10:00:00'),
(1, 'WH-WEST', 'B-02-03', 50, 0, 15, '2024-02-14 14:30:00'),
(2, 'WH-EAST', 'A-01-02', 150, 10, 25, '2024-02-15 10:00:00'),
(2, 'WH-WEST', 'B-02-04', 50, 0, 15, '2024-02-14 14:30:00'),
(3, 'WH-EAST', 'A-02-01', 60, 3, 15, '2024-02-15 11:00:00'),
(3, 'WH-WEST', 'B-03-01', 20, 0, 10, '2024-02-14 15:00:00'),
(4, 'WH-EAST', 'C-01-01', 30, 2, 10, '2024-02-15 11:30:00'),
(4, 'WH-WEST', 'C-01-02', 15, 0, 8, '2024-02-14 15:30:00'),
(5, 'WH-EAST', 'D-01-01', 80, 5, 20, '2024-02-15 12:00:00'),
(5, 'WH-WEST', 'D-01-02', 40, 0, 15, '2024-02-14 16:00:00');

-- =============================================================================
-- Table: inventory_movements
-- Tests: DATETIME PRECISION, REFERENCE TO MULTIPLE TABLES
-- =============================================================================
CREATE TABLE inventory_movements (
    movement_id BIGINT AUTO_INCREMENT PRIMARY KEY,
    product_id INT NOT NULL,
    warehouse_code VARCHAR(10) NOT NULL,
    movement_type ENUM('receipt', 'shipment', 'adjustment', 'transfer_in', 'transfer_out', 'return') NOT NULL,
    quantity INT NOT NULL,
    reference_type VARCHAR(50),  -- 'purchase_order', 'sales_order', 'transfer', etc.
    reference_id VARCHAR(50),
    from_location VARCHAR(20),
    to_location VARCHAR(20),
    reason VARCHAR(200),
    performed_by INT,
    movement_date DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
    FOREIGN KEY (product_id) REFERENCES products(product_id),
    FOREIGN KEY (performed_by) REFERENCES users(user_id),
    INDEX idx_product (product_id),
    INDEX idx_warehouse (warehouse_code),
    INDEX idx_date (movement_date)
) ENGINE=InnoDB;

INSERT INTO inventory_movements (product_id, warehouse_code, movement_type, quantity, reference_type, reference_id, to_location, performed_by, movement_date) VALUES
(1, 'WH-EAST', 'receipt', 50, 'purchase_order', 'PO-2024-0015', 'A-01-01', 3, '2024-02-10 09:30:00.123'),
(2, 'WH-EAST', 'receipt', 100, 'purchase_order', 'PO-2024-0015', 'A-01-02', 3, '2024-02-10 09:35:00.456'),
(1, 'WH-EAST', 'shipment', -5, 'sales_order', 'SO-2024-0042', NULL, 3, '2024-02-12 14:20:00.789'),
(3, 'WH-EAST', 'adjustment', -2, NULL, NULL, NULL, 2, '2024-02-14 16:00:00.000'),
(5, 'WH-WEST', 'transfer_in', 20, 'transfer', 'TR-2024-0008', 'D-01-02', 3, '2024-02-15 10:00:00.100');

-- =============================================================================
-- Table: payment_transactions
-- Tests: DECIMAL FOR CURRENCY, ENUM FOR STATUS, TIMESTAMPS
-- =============================================================================
CREATE TABLE payment_transactions (
    transaction_id BIGINT AUTO_INCREMENT PRIMARY KEY,
    transaction_ref VARCHAR(50) NOT NULL UNIQUE,
    user_id INT,
    amount DECIMAL(12,2) NOT NULL,
    currency CHAR(3) DEFAULT 'USD',
    payment_method ENUM('credit_card', 'debit_card', 'paypal', 'bank_transfer', 'crypto', 'cash') NOT NULL,
    card_last_four CHAR(4),
    card_brand VARCHAR(20),
    billing_name VARCHAR(100),
    billing_email VARCHAR(150),
    billing_address TEXT,
    status ENUM('pending', 'processing', 'completed', 'failed', 'refunded', 'cancelled') DEFAULT 'pending',
    failure_reason VARCHAR(255),
    gateway_response JSON,
    ip_address VARCHAR(45),
    initiated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    completed_at DATETIME,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(user_id),
    INDEX idx_user (user_id),
    INDEX idx_status (status),
    INDEX idx_date (initiated_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

INSERT INTO payment_transactions (transaction_ref, user_id, amount, currency, payment_method, card_last_four, card_brand, billing_name, billing_email, status, gateway_response, ip_address, initiated_at, completed_at) VALUES
('TXN-2024-00001', 4, 59.99, 'USD', 'credit_card', '4242', 'Visa', 'Alice Customer', 'alice@email.com', 'completed', '{"auth_code": "ABC123", "processor": "stripe"}', '192.168.1.50', '2024-02-15 11:20:00', '2024-02-15 11:20:05'),
('TXN-2024-00002', 6, 159.98, 'USD', 'paypal', NULL, NULL, 'Diana Prince', 'diana@email.com', 'completed', '{"paypal_id": "PAY-123456"}', '10.0.0.100', '2024-02-16 14:30:00', '2024-02-16 14:30:12'),
('TXN-2024-00003', 4, 199.99, 'USD', 'credit_card', '1234', 'Mastercard', 'Alice Customer', 'alice@email.com', 'completed', '{"auth_code": "DEF456"}', '192.168.1.50', '2024-02-17 09:15:00', '2024-02-17 09:15:08'),
('TXN-2024-00004', NULL, 89.99, 'USD', 'credit_card', '5678', 'Visa', 'Guest User', 'guest@email.com', 'failed', '{"error": "insufficient_funds"}', '203.0.113.50', '2024-02-18 16:45:00', NULL),
('TXN-2024-00005', 6, 44.99, 'EUR', 'bank_transfer', NULL, NULL, 'Diana Prince', 'diana@email.com', 'pending', NULL, '10.0.0.100', '2024-02-20 10:00:00', NULL);

SELECT 'MySQL seed data loaded successfully!' AS status;
