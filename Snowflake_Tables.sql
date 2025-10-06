-- 1. Tables
-- ==================================================

CREATE OR REPLACE TABLE CUSTOMERS (
    customer_id STRING PRIMARY KEY,
    customer_name STRING,
    email STRING,
    phone STRING,
    region STRING,
    signup_date DATE
);

CREATE OR REPLACE TABLE PRODUCTS (
    product_id STRING PRIMARY KEY,
    product_name STRING,
    category STRING,
    supplier_id STRING
);

CREATE OR REPLACE TABLE ORDERS (
    order_id STRING PRIMARY KEY,
    customer_id STRING REFERENCES CUSTOMERS(customer_id),
    order_date DATE,
    order_status STRING,
    total_amount NUMBER(12,2),
    discount_amount NUMBER(12,2),
    channel STRING,
    region STRING
);

CREATE OR REPLACE TABLE ORDER_ITEMS (
    order_item_id STRING PRIMARY KEY,
    order_id STRING REFERENCES ORDERS(order_id),
    product_id STRING REFERENCES PRODUCTS(product_id),
    quantity INT,
    unit_price NUMBER(10,2),
    discount NUMBER(5,2)
);

CREATE OR REPLACE TABLE REFUNDS (
    refund_id STRING PRIMARY KEY,
    order_id STRING REFERENCES ORDERS(order_id),
    refund_amount NUMBER(12,2),
    refund_date DATE
);

CREATE OR REPLACE TABLE SHIPMENTS (
    shipment_id STRING PRIMARY KEY,
    order_id STRING REFERENCES ORDERS(order_id),
    shipped_date DATE,
    delivered_date DATE,
    supplier_id STRING,
    shipping_delay_days INT
);

CREATE OR REPLACE TABLE INVENTORY (
    product_id STRING REFERENCES PRODUCTS(product_id),
    stock_quantity INT,
    last_updated TIMESTAMP
);

CREATE OR REPLACE TABLE CAMPAIGNS (
    campaign_id STRING PRIMARY KEY,
    campaign_name STRING,
    start_date DATE,
    end_date DATE,
    budget NUMBER(12,2)
);

CREATE OR REPLACE TABLE CAMPAIGN_TOUCHES (
    touch_id STRING PRIMARY KEY,
    campaign_id STRING REFERENCES CAMPAIGNS(campaign_id),
    customer_id STRING REFERENCES CUSTOMERS(customer_id),
    touch_date DATE,
    variant STRING
);

-- ==================================================
-- 2. Sample Data
-- ==================================================

-- Customers
INSERT INTO CUSTOMERS VALUES
('C001', 'Alice Johnson', 'alice@example.com', '1234567890', 'North', '2024-01-15'),
('C002', 'Bob Smith', 'bob@example.com', '9876543210', 'South', '2024-02-20'),
('C003', 'Carla Lopez', 'carla@example.com', '4567891230', 'East', '2024-05-10');

-- Products
INSERT INTO PRODUCTS VALUES
('P001', 'Smartphone X', 'Electronics', 'SUP01'),
('P002', 'Laptop Z', 'Electronics', 'SUP01'),
('P003', 'T-shirt Blue', 'Apparel', 'SUP02');

-- Orders
INSERT INTO ORDERS VALUES
('O1001', 'C001', '2025-07-10', 'PAID', 600, 50, 'Web', 'North'),
('O1002', 'C002', '2025-07-15', 'PAID', 1200, 0, 'Mobile', 'South'),
('O1003', 'C003', '2025-07-20', 'PAID', 800, 0, 'Web', 'East'),
('O1004', 'C001', '2025-08-05', 'PAID', 300, 0, 'Web', 'North'),
('O1005', 'C002', '2025-08-12', 'PAID', 400, 0, 'Mobile', 'South');

-- Order Items
INSERT INTO ORDER_ITEMS VALUES
('OI1', 'O1001', 'P001', 1, 600, 0.083),   -- Smartphone, July
('OI2', 'O1002', 'P002', 1, 1200, 0),     -- Laptop, July
('OI3', 'O1003', 'P003', 4, 200, 0),      -- T-shirts, July
('OI4', 'O1004', 'P001', 1, 300, 0),      -- Smartphone, Aug
('OI5', 'O1005', 'P003', 2, 200, 0);      -- T-shirts, Aug

-- Refunds
INSERT INTO REFUNDS VALUES
('R1001', 'O1001', 50, '2025-07-18'),
('R1002', 'O1005', 100, '2025-08-20');

-- Shipments
INSERT INTO SHIPMENTS VALUES
('S1001', 'O1001', '2025-07-11', '2025-07-13', 'SUP01', 2),
('S1002', 'O1004', '2025-08-06', '2025-08-12', 'SUP01', 6);

-- Inventory
INSERT INTO INVENTORY VALUES
('P001', 0, '2025-08-07 10:00:00'),   -- Smartphone out of stock in Aug
('P002', 10, '2025-07-15 12:00:00'),
('P003', 50, '2025-07-20 15:00:00');

-- Campaigns
INSERT INTO CAMPAIGNS VALUES
('CAM01', 'Electronics July Promo', '2025-07-01', '2025-07-31', 5000),
('CAM02', 'Electronics August Promo', '2025-08-01', '2025-08-31', 2000);

-- Campaign Touches
INSERT INTO CAMPAIGN_TOUCHES VALUES
('T001', 'CAM01', 'C001', '2025-07-05', 'EmailA'),
('T002', 'CAM01', 'C002', '2025-07-10', 'EmailB'),
('T003', 'CAM02', 'C001', '2025-08-02', 'EmailA');
