-- =============================================================================
-- DA-MACAÉ :: Azure SQL Database Seed Data
-- =============================================================================
-- Compatible with Azure SQL Database (all tiers)
-- Run against your Azure SQL Database instance
-- =============================================================================

-- Note: Database should already exist in Azure. Remove CREATE DATABASE if needed.
-- CREATE DATABASE source_db;
-- GO

-- Drop existing tables if they exist (in dependency order)
IF OBJECT_ID('dbo.order_items', 'U') IS NOT NULL DROP TABLE dbo.order_items;
IF OBJECT_ID('dbo.orders', 'U') IS NOT NULL DROP TABLE dbo.orders;
IF OBJECT_ID('dbo.products', 'U') IS NOT NULL DROP TABLE dbo.products;
IF OBJECT_ID('dbo.categories', 'U') IS NOT NULL DROP TABLE dbo.categories;
IF OBJECT_ID('dbo.customers', 'U') IS NOT NULL DROP TABLE dbo.customers;
IF OBJECT_ID('dbo.employees', 'U') IS NOT NULL DROP TABLE dbo.employees;
IF OBJECT_ID('dbo.departments', 'U') IS NOT NULL DROP TABLE dbo.departments;
IF OBJECT_ID('dbo.audit_log', 'U') IS NOT NULL DROP TABLE dbo.audit_log;
GO

-- =============================================================================
-- Table: departments
-- =============================================================================
CREATE TABLE dbo.departments (
    department_id INT IDENTITY(1,1) PRIMARY KEY,
    department_name NVARCHAR(100) NOT NULL,
    department_code VARCHAR(10) NOT NULL UNIQUE,
    budget DECIMAL(15,2) DEFAULT 0,
    created_at DATETIME2 DEFAULT GETDATE(),
    is_active BIT DEFAULT 1
);
GO

INSERT INTO dbo.departments (department_name, department_code, budget) VALUES
('Engineering', 'ENG', 500000.00),
('Sales', 'SAL', 350000.00),
('Marketing', 'MKT', 250000.00),
('Human Resources', 'HR', 150000.00),
('Finance', 'FIN', 200000.00);
GO

-- =============================================================================
-- Table: employees
-- =============================================================================
CREATE TABLE dbo.employees (
    employee_id INT IDENTITY(100,1) PRIMARY KEY,
    first_name NVARCHAR(50) NOT NULL,
    last_name NVARCHAR(50) NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    phone VARCHAR(20),
    hire_date DATE NOT NULL,
    salary MONEY NOT NULL,
    bonus_pct DECIMAL(5,2) DEFAULT 0,
    department_id INT,
    manager_id INT,
    full_name AS (first_name + ' ' + last_name) PERSISTED,
    created_at DATETIME2 DEFAULT GETDATE(),
    updated_at DATETIME2,
    CONSTRAINT FK_emp_dept FOREIGN KEY (department_id) REFERENCES dbo.departments(department_id),
    CONSTRAINT FK_emp_mgr FOREIGN KEY (manager_id) REFERENCES dbo.employees(employee_id)
);
GO

INSERT INTO dbo.employees (first_name, last_name, email, phone, hire_date, salary, bonus_pct, department_id, manager_id) VALUES
('John', 'Smith', 'john.smith@company.com', '+1-555-0101', '2020-01-15', 95000.00, 10.00, 1, NULL),
('Sarah', 'Johnson', 'sarah.j@company.com', '+1-555-0102', '2020-03-20', 85000.00, 8.50, 1, 100),
('Michael', 'Williams', 'mwilliams@company.com', '+1-555-0103', '2019-06-01', 78000.00, 7.00, 2, NULL),
('Emily', 'Brown', 'emily.brown@company.com', NULL, '2021-02-14', 72000.00, 5.00, 2, 102),
('David', 'Davis', 'ddavis@company.com', '+1-555-0105', '2018-11-30', 110000.00, 15.00, 1, 100),
('Jessica', 'Miller', 'jmiller@company.com', '+1-555-0106', '2022-04-10', 65000.00, 0, 3, NULL),
('Robert', 'Wilson', 'rwilson@company.com', '+1-555-0107', '2021-08-22', 82000.00, 6.50, 4, NULL),
('Amanda', 'Taylor', 'ataylor@company.com', '+1-555-0108', '2020-09-05', 75000.00, 5.50, 5, NULL);
GO

-- =============================================================================
-- Table: categories
-- =============================================================================
CREATE TABLE dbo.categories (
    category_id INT IDENTITY(1,1) PRIMARY KEY,
    category_guid UNIQUEIDENTIFIER DEFAULT NEWID(),
    category_name NVARCHAR(100) NOT NULL,
    parent_category_id INT,
    description NVARCHAR(500),
    sort_order SMALLINT DEFAULT 0,
    CONSTRAINT FK_cat_parent FOREIGN KEY (parent_category_id) REFERENCES dbo.categories(category_id)
);
GO

INSERT INTO dbo.categories (category_name, parent_category_id, description, sort_order) VALUES
('Electronics', NULL, 'Electronic devices and accessories', 1),
('Computers', 1, 'Desktop and laptop computers', 1),
('Laptops', 2, 'Portable computers', 1),
('Desktops', 2, 'Desktop workstations', 2),
('Mobile Devices', 1, 'Smartphones and tablets', 2),
('Home & Garden', NULL, 'Home improvement and garden supplies', 2),
('Furniture', 6, 'Indoor and outdoor furniture', 1),
('Kitchen', 6, 'Kitchen appliances and tools', 2);
GO

-- =============================================================================
-- Table: products
-- =============================================================================
CREATE TABLE dbo.products (
    product_id INT IDENTITY(1000,1) PRIMARY KEY,
    sku VARCHAR(50) NOT NULL UNIQUE,
    product_name NVARCHAR(200) NOT NULL,
    description NVARCHAR(MAX),
    category_id INT NOT NULL,
    unit_price DECIMAL(10,2) NOT NULL,
    cost_price DECIMAL(10,2),
    quantity_in_stock INT DEFAULT 0,
    reorder_level INT DEFAULT 10,
    weight_kg FLOAT,
    dimensions_json NVARCHAR(500),
    product_image VARBINARY(MAX),
    is_discontinued BIT DEFAULT 0,
    created_at DATETIME2 DEFAULT GETDATE(),
    CONSTRAINT FK_prod_cat FOREIGN KEY (category_id) REFERENCES dbo.categories(category_id)
);
GO

INSERT INTO dbo.products (sku, product_name, description, category_id, unit_price, cost_price, quantity_in_stock, reorder_level, weight_kg, dimensions_json) VALUES
('LAPTOP-PRO-15', 'ProBook Laptop 15"', 'High-performance laptop with 15.6" display, 16GB RAM, 512GB SSD', 3, 1299.99, 950.00, 50, 10, 2.1, '{"length": 35.8, "width": 24.2, "height": 1.8, "unit": "cm"}'),
('LAPTOP-AIR-13', 'AirBook Laptop 13"', 'Ultra-thin laptop with 13.3" Retina display, 8GB RAM, 256GB SSD', 3, 999.99, 720.00, 75, 15, 1.3, '{"length": 30.4, "width": 21.2, "height": 1.1, "unit": "cm"}'),
('DESKTOP-WS-01', 'Workstation Pro', 'Professional desktop workstation, 32GB RAM, 1TB NVMe', 4, 1899.99, 1400.00, 25, 5, 8.5, '{"length": 45.0, "width": 20.0, "height": 40.0, "unit": "cm"}'),
('PHONE-X-128', 'SmartPhone X 128GB', 'Latest smartphone with 128GB storage and 5G support', 5, 899.99, 650.00, 200, 50, 0.18, '{"length": 14.6, "width": 7.1, "height": 0.8, "unit": "cm"}'),
('TABLET-10', 'ProTab 10"', '10.1" tablet with stylus support, 64GB storage', 5, 549.99, 380.00, 80, 20, 0.45, '{"length": 24.7, "width": 17.4, "height": 0.6, "unit": "cm"}'),
('CHAIR-ERGO', 'Ergonomic Office Chair', 'Adjustable ergonomic chair with lumbar support', 7, 349.99, 180.00, 40, 10, 15.0, '{"length": 65.0, "width": 65.0, "height": 120.0, "unit": "cm"}'),
('DESK-STAND', 'Standing Desk', 'Electric height-adjustable standing desk', 7, 599.99, 350.00, 30, 8, 45.0, '{"length": 150.0, "width": 75.0, "height": 120.0, "unit": "cm"}'),
('BLENDER-PRO', 'Professional Blender', 'High-power blender with multiple speed settings', 8, 199.99, 95.00, 60, 15, 4.2, '{"length": 20.0, "width": 20.0, "height": 45.0, "unit": "cm"}');
GO

-- =============================================================================
-- Table: customers
-- =============================================================================
CREATE TABLE dbo.customers (
    customer_id INT IDENTITY(1,1) PRIMARY KEY,
    customer_code VARCHAR(20) NOT NULL UNIQUE,
    company_name NVARCHAR(150),
    contact_name NVARCHAR(100) NOT NULL,
    contact_email VARCHAR(150) NOT NULL,
    contact_phone VARCHAR(30),
    billing_address NVARCHAR(200),
    billing_city NVARCHAR(100),
    billing_state VARCHAR(50),
    billing_postal_code VARCHAR(20),
    billing_country VARCHAR(50) DEFAULT 'USA',
    shipping_address NVARCHAR(200),
    shipping_city NVARCHAR(100),
    shipping_state VARCHAR(50),
    shipping_postal_code VARCHAR(20),
    shipping_country VARCHAR(50) DEFAULT 'USA',
    latitude DECIMAL(9,6),
    longitude DECIMAL(9,6),
    credit_limit MONEY DEFAULT 0,
    account_status VARCHAR(20) DEFAULT 'Active',
    date_of_birth DATE,
    registration_date DATETIME DEFAULT GETDATE(),
    last_order_date DATETIME,
    notes NVARCHAR(MAX)
);
GO

INSERT INTO dbo.customers (customer_code, company_name, contact_name, contact_email, contact_phone, billing_address, billing_city, billing_state, billing_postal_code, shipping_address, shipping_city, shipping_state, shipping_postal_code, latitude, longitude, credit_limit, date_of_birth) VALUES
('CUST-001', 'Acme Corporation', 'John Doe', 'jdoe@acme.com', '+1-555-1001', '123 Main St', 'New York', 'NY', '10001', '123 Main St', 'New York', 'NY', '10001', 40.712776, -74.005974, 50000.00, '1985-03-15'),
('CUST-002', 'TechStart Inc', 'Jane Smith', 'jsmith@techstart.io', '+1-555-1002', '456 Tech Blvd', 'San Francisco', 'CA', '94102', '456 Tech Blvd', 'San Francisco', 'CA', '94102', 37.774929, -122.419416, 75000.00, '1990-07-22'),
('CUST-003', NULL, 'Bob Wilson', 'bwilson@email.com', '+1-555-1003', '789 Oak Ave', 'Chicago', 'IL', '60601', '789 Oak Ave', 'Chicago', 'IL', '60601', 41.878113, -87.629799, 25000.00, '1978-11-08'),
('CUST-004', 'Global Traders LLC', 'Alice Brown', 'abrown@globaltraders.com', '+1-555-1004', '321 Commerce Way', 'Houston', 'TX', '77001', '999 Warehouse Rd', 'Houston', 'TX', '77002', 29.760427, -95.369803, 100000.00, '1982-05-30'),
('CUST-005', 'Local Shop', 'Charlie Green', 'charlie@localshop.net', NULL, '555 Market St', 'Seattle', 'WA', '98101', '555 Market St', 'Seattle', 'WA', '98101', 47.606209, -122.332071, 15000.00, '1995-12-01');
GO

-- =============================================================================
-- Table: orders
-- =============================================================================
CREATE TABLE dbo.orders (
    order_id INT IDENTITY(10000,1) PRIMARY KEY,
    order_number VARCHAR(30) NOT NULL UNIQUE,
    customer_id INT NOT NULL,
    employee_id INT,
    order_date DATETIME2(3) NOT NULL DEFAULT GETDATE(),
    required_date DATE,
    shipped_date DATETIME2(3),
    ship_via VARCHAR(50),
    freight MONEY DEFAULT 0,
    subtotal MONEY NOT NULL,
    tax_amount MONEY DEFAULT 0,
    discount_amount MONEY DEFAULT 0,
    total_amount AS (subtotal + ISNULL(tax_amount, 0) - ISNULL(discount_amount, 0)) PERSISTED,
    order_status VARCHAR(20) NOT NULL DEFAULT 'Pending',
    payment_method VARCHAR(30),
    payment_status VARCHAR(20) DEFAULT 'Unpaid',
    notes NVARCHAR(1000),
    CONSTRAINT FK_ord_cust FOREIGN KEY (customer_id) REFERENCES dbo.customers(customer_id),
    CONSTRAINT FK_ord_emp FOREIGN KEY (employee_id) REFERENCES dbo.employees(employee_id),
    CONSTRAINT CHK_status CHECK (order_status IN ('Pending', 'Processing', 'Shipped', 'Delivered', 'Cancelled'))
);
GO

INSERT INTO dbo.orders (order_number, customer_id, employee_id, order_date, required_date, shipped_date, ship_via, freight, subtotal, tax_amount, discount_amount, order_status, payment_method, payment_status) VALUES
('ORD-2024-0001', 1, 102, '2024-01-15 09:30:00', '2024-01-22', '2024-01-17 14:00:00', 'FedEx Ground', 25.00, 1299.99, 104.00, 0, 'Delivered', 'Credit Card', 'Paid'),
('ORD-2024-0002', 2, 103, '2024-01-18 11:15:00', '2024-01-25', '2024-01-20 10:30:00', 'UPS', 35.00, 2199.98, 175.99, 50.00, 'Delivered', 'Credit Card', 'Paid'),
('ORD-2024-0003', 1, 102, '2024-02-01 14:45:00', '2024-02-08', NULL, 'FedEx Express', 45.00, 899.99, 72.00, 0, 'Processing', 'PayPal', 'Paid'),
('ORD-2024-0004', 3, 103, '2024-02-10 16:20:00', '2024-02-17', '2024-02-14 09:00:00', 'USPS Priority', 15.00, 549.99, 44.00, 25.00, 'Shipped', 'Credit Card', 'Paid'),
('ORD-2024-0005', 4, 102, '2024-02-15 08:00:00', '2024-02-22', NULL, 'FedEx Ground', 55.00, 3249.97, 260.00, 100.00, 'Pending', 'Net 30', 'Unpaid'),
('ORD-2024-0006', 5, NULL, '2024-02-20 13:30:00', '2024-02-27', NULL, NULL, 0, 199.99, 16.00, 0, 'Cancelled', 'Credit Card', 'Refunded');
GO

-- =============================================================================
-- Table: order_items
-- =============================================================================
CREATE TABLE dbo.order_items (
    order_id INT NOT NULL,
    line_number SMALLINT NOT NULL,
    product_id INT NOT NULL,
    quantity INT NOT NULL DEFAULT 1,
    unit_price DECIMAL(10,2) NOT NULL,
    discount_pct DECIMAL(5,2) DEFAULT 0,
    line_total AS (quantity * unit_price * (1 - ISNULL(discount_pct, 0) / 100)) PERSISTED,
    CONSTRAINT PK_order_items PRIMARY KEY (order_id, line_number),
    CONSTRAINT FK_oi_order FOREIGN KEY (order_id) REFERENCES dbo.orders(order_id),
    CONSTRAINT FK_oi_prod FOREIGN KEY (product_id) REFERENCES dbo.products(product_id)
);
GO

INSERT INTO dbo.order_items (order_id, line_number, product_id, quantity, unit_price, discount_pct) VALUES
(10000, 1, 1000, 1, 1299.99, 0),
(10001, 1, 1000, 1, 1299.99, 0),
(10001, 2, 1003, 1, 899.99, 0),
(10002, 1, 1003, 1, 899.99, 0),
(10003, 1, 1004, 1, 549.99, 5.00),
(10004, 1, 1002, 1, 1899.99, 0),
(10004, 2, 1005, 1, 349.99, 10.00),
(10004, 3, 1006, 1, 599.99, 0),
(10005, 1, 1007, 1, 199.99, 0);
GO

-- =============================================================================
-- Table: audit_log
-- =============================================================================
CREATE TABLE dbo.audit_log (
    log_id BIGINT IDENTITY(1,1) PRIMARY KEY,
    event_time DATETIMEOFFSET NOT NULL DEFAULT SYSDATETIMEOFFSET(),
    event_type VARCHAR(50) NOT NULL,
    table_name VARCHAR(100),
    record_id VARCHAR(50),
    user_name NVARCHAR(100),
    old_values NVARCHAR(MAX),
    new_values NVARCHAR(MAX),
    ip_address VARCHAR(45),
    user_agent NVARCHAR(500)
);
GO

INSERT INTO dbo.audit_log (event_type, table_name, record_id, user_name, old_values, new_values, ip_address) VALUES
('INSERT', 'orders', '10000', 'system', NULL, '{"order_number": "ORD-2024-0001", "customer_id": 1}', '192.168.1.100'),
('UPDATE', 'orders', '10000', 'jsmith', '{"order_status": "Pending"}', '{"order_status": "Processing"}', '192.168.1.101'),
('UPDATE', 'orders', '10000', 'jsmith', '{"order_status": "Processing"}', '{"order_status": "Shipped"}', '192.168.1.101'),
('INSERT', 'customers', '5', 'admin', NULL, '{"customer_code": "CUST-005", "contact_name": "Charlie Green"}', '10.0.0.50'),
('DELETE', 'products', '9999', 'admin', '{"sku": "DISCONTINUED-01", "product_name": "Old Product"}', NULL, '10.0.0.50');
GO

PRINT 'Azure SQL Database seed data loaded successfully!';
GO
