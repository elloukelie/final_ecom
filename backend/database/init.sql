-- Drop tables if they exist to allow for clean re-creation during development
-- IMPORTANT: Drop in reverse order of foreign key dependencies
DROP TABLE IF EXISTS order_item;
DROP TABLE IF EXISTS `order`;
DROP TABLE IF EXISTS customer;
DROP TABLE IF EXISTS product;
DROP TABLE IF EXISTS `user`; -- <--- NEW: Drop user table first if it depends on nothing, or after tables that depend on it


-- Create User table -- <--- NEW TABLE
CREATE TABLE `user` (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    email VARCHAR(255) UNIQUE, -- Optional: you might want users to have emails
    is_active BOOLEAN DEFAULT TRUE,
    is_admin BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);


-- Create Customer table (linked to User table)
CREATE TABLE customer (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT UNIQUE NOT NULL,  -- Link each customer to a user account
    first_name VARCHAR(255) NOT NULL,
    last_name VARCHAR(255) NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    phone VARCHAR(20),
    address TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES `user`(id) ON DELETE CASCADE
);

-- Create Product table (existing, with stock_quantity and updated_at)
CREATE TABLE product (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    price DECIMAL(10, 2) NOT NULL,
    stock_quantity INT NOT NULL DEFAULT 0,
    image_url VARCHAR(500),
    image_alt_text VARCHAR(255),
    category VARCHAR(100),
    brand VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

-- Create 'order' table (existing)
CREATE TABLE `order` (
    id INT AUTO_INCREMENT PRIMARY KEY,
    customer_id INT NOT NULL,
    order_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    total_amount DECIMAL(10, 2) NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'PENDING',
    FOREIGN KEY (customer_id) REFERENCES customer(id)
);

-- Create 'order_item' table (existing)
CREATE TABLE order_item (
    id INT AUTO_INCREMENT PRIMARY KEY,
    order_id INT NOT NULL,
    product_id INT NOT NULL,
    quantity INT NOT NULL,
    price_at_order DECIMAL(10, 2) NOT NULL,
    FOREIGN KEY (order_id) REFERENCES `order`(id) ON DELETE CASCADE,
    FOREIGN KEY (product_id) REFERENCES product(id)
);

-- Create cart table for persistent shopping cart
CREATE TABLE cart (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    product_id INT NOT NULL,
    quantity INT NOT NULL DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES `user`(id) ON DELETE CASCADE,
    FOREIGN KEY (product_id) REFERENCES product(id) ON DELETE CASCADE,
    UNIQUE KEY unique_user_product (user_id, product_id)
);

-- Create favorites table for persistent favorites
CREATE TABLE favorites (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    product_id INT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES `user`(id) ON DELETE CASCADE,
    FOREIGN KEY (product_id) REFERENCES product(id) ON DELETE CASCADE,
    UNIQUE KEY unique_user_favorite (user_id, product_id)
);

-- --- USER DATA INSERTS ---
-- Create admin user with username 'admin', password 'admin', and admin privileges
INSERT INTO `user` (username, password_hash, email, is_admin) VALUES
('admin', '$2b$12$ged0EuBGoXOrdYtfT6UppOu/c9lcAglmVv8z8IfU3DmQKDQuqeISa', 'admin@example.com', TRUE);

-- Create customer users with username as firstname and password as firstname
-- Alice Smith: username 'alice', password 'alice'
-- Bob Johnson: username 'bob', password 'bob'
-- Additional test users for ML Analytics
INSERT INTO `user` (username, password_hash, email, is_admin) VALUES
('alice', '$2b$12$xrwHLGJUTHzEqNFPosT1H.TrXlVEq3J7MyAVpVxFyDJKI5whFmz5u', 'alice.smith@example.com', FALSE),
('bob', '$2b$12$gKuGKrWyO03Uirbl5B/HBuJ3JcAe.cVVE44Hv5ovG9ls.jznf0Ha.', 'bob.johnson@example.com', FALSE),
('charlie', '$2b$12$xrwHLGJUTHzEqNFPosT1H.TrXlVEq3J7MyAVpVxFyDJKI5whFmz5u', 'charlie.brown@example.com', FALSE),
('diana', '$2b$12$gKuGKrWyO03Uirbl5B/HBuJ3JcAe.cVVE44Hv5ovG9ls.jznf0Ha.', 'diana.prince@example.com', FALSE),
('emma', '$2b$12$xrwHLGJUTHzEqNFPosT1H.TrXlVEq3J7MyAVpVxFyDJKI5whFmz5u', 'emma.watson@example.com', FALSE),
('frank', '$2b$12$gKuGKrWyO03Uirbl5B/HBuJ3JcAe.cVVE44Hv5ovG9ls.jznf0Ha.', 'frank.miller@example.com', FALSE),
('grace', '$2b$12$xrwHLGJUTHzEqNFPosT1H.TrXlVEq3J7MyAVpVxFyDJKI5whFmz5u', 'grace.kelly@example.com', FALSE),
('henry', '$2b$12$gKuGKrWyO03Uirbl5B/HBuJ3JcAe.cVVE44Hv5ovG9ls.jznf0Ha.', 'henry.ford@example.com', FALSE),
('iris', '$2b$12$xrwHLGJUTHzEqNFPosT1H.TrXlVEq3J7MyAVpVxFyDJKI5whFmz5u', 'iris.west@example.com', FALSE),
('jack', '$2b$12$gKuGKrWyO03Uirbl5B/HBuJ3JcAe.cVVE44Hv5ovG9ls.jznf0Ha.', 'jack.sparrow@example.com', FALSE),
('demo', '$2b$12$xrwHLGJUTHzEqNFPosT1H.TrXlVEq3J7MyAVpVxFyDJKI5whFmz5u', 'demo@example.com', FALSE),
('testuser', '$2b$12$gKuGKrWyO03Uirbl5B/HBuJ3JcAe.cVVE44Hv5ovG9ls.jznf0Ha.', 'test@example.com', FALSE),
('sarah', '$2b$12$xrwHLGJUTHzEqNFPosT1H.TrXlVEq3J7MyAVpVxFyDJKI5whFmz5u', 'sarah.connor@example.com', FALSE);

-- Insert customers linked to their user accounts with diverse profiles
INSERT INTO customer (user_id, first_name, last_name, email, phone, address) VALUES
(2, 'Alice', 'Smith', 'alice.smith@example.com', '+1-555-0123', '123 Main St, New York, NY 10001'),
(3, 'Bob', 'Johnson', 'bob.johnson@example.com', '+1-555-0456', '456 Oak Ave, Los Angeles, CA 90210'),
(4, 'Charlie', 'Brown', 'charlie.brown@example.com', '+1-555-0789', '789 Pine St, Chicago, IL 60601'),
(5, 'Diana', 'Prince', 'diana.prince@example.com', '+1-555-0321', '321 Elm St, Miami, FL 33101'),
(6, 'Emma', 'Watson', 'emma.watson@example.com', '+1-555-0654', '654 Maple Ave, Seattle, WA 98101'),
(7, 'Frank', 'Miller', 'frank.miller@example.com', '+1-555-0987', '987 Cedar Rd, Austin, TX 73301'),
(8, 'Grace', 'Kelly', 'grace.kelly@example.com', '+1-555-0147', '147 Birch Ln, Denver, CO 80201'),
(9, 'Henry', 'Ford', 'henry.ford@example.com', '+1-555-0258', '258 Spruce St, Portland, OR 97201'),
(10, 'Iris', 'West', 'iris.west@example.com', '+1-555-0369', '369 Willow Dr, Phoenix, AZ 85001'),
(11, 'Jack', 'Sparrow', 'jack.sparrow@example.com', '+1-555-0741', '741 Ocean Blvd, San Diego, CA 92101'),
(12, 'Demo', 'User', 'demo@example.com', '+1-555-0852', '852 Demo St, Demo City, DC 12345'),
(13, 'Test', 'User', 'test@example.com', '+1-555-0963', '963 Test Ave, Test Town, TT 67890'),
(14, 'Sarah', 'Connor', 'sarah.connor@example.com', '+1-555-0159', '159 Resistance Blvd, Future City, FC 20291');

INSERT INTO product (name, description, price, stock_quantity, image_url, image_alt_text, category, brand) VALUES
('MacBook Pro 16"', 'Powerful laptop with M3 Pro chip, 18GB RAM, and 512GB SSD. Perfect for developers and creative professionals.', 2499.00, 25, '/static/images/macbook-pro.jpg', 'MacBook Pro 16 inch laptop', 'Laptops', 'Apple'),
('Dell XPS 13', 'Ultra-portable laptop with 13-inch InfinityEdge display, Intel i7 processor, and premium build quality.', 1299.00, 40, '/static/images/dell-xps-13.jpg', 'Dell XPS 13 ultrabook', 'Laptops', 'Dell'),
('Logitech MX Master 3S', 'Advanced wireless mouse with precise tracking, customizable buttons, and ergonomic design.', 99.99, 150, '/static/images/logitech-mx-master.jpg', 'Logitech MX Master 3S wireless mouse', 'Accessories', 'Logitech'),
('Mechanical Keyboard RGB', 'Premium mechanical keyboard with Cherry MX switches, RGB backlighting, and programmable keys.', 149.99, 75, '/static/images/mechanical-keyboard.jpg', 'RGB mechanical gaming keyboard', 'Accessories', 'Corsair'),
('iPhone 15 Pro', 'Latest iPhone with A17 Pro chip, Pro camera system, and titanium design. Available in multiple colors.', 999.00, 60, '/static/images/iphone-15-pro.jpg', 'iPhone 15 Pro smartphone', 'Smartphones', 'Apple'),
('Samsung Galaxy S24 Ultra', 'Premium Android phone with S Pen, 200MP camera, and large 6.8-inch Dynamic AMOLED display.', 1199.00, 45, '/static/images/samsung-s24-ultra.jpg', 'Samsung Galaxy S24 Ultra phone', 'Smartphones', 'Samsung'),
('Sony WH-1000XM5', 'Industry-leading noise canceling headphones with exceptional sound quality and 30-hour battery life.', 399.99, 80, '/static/images/sony-headphones.jpg', 'Sony WH-1000XM5 noise canceling headphones', 'Audio', 'Sony'),
('iPad Air 5th Gen', 'Versatile tablet with M1 chip, 10.9-inch Liquid Retina display, and support for Apple Pencil.', 599.00, 35, '/static/images/ipad-air.jpg', 'iPad Air 5th generation tablet', 'Tablets', 'Apple'),
('ASUS ROG Gaming Monitor', '27-inch 4K gaming monitor with 144Hz refresh rate, G-Sync compatible, and HDR support.', 649.99, 20, '/static/images/asus-monitor.jpg', 'ASUS ROG 27-inch gaming monitor', 'Monitors', 'ASUS'),
('Razer DeathAdder V3', 'Ergonomic gaming mouse with Focus Pro sensor, ultra-lightweight design, and customizable RGB.', 79.99, 120, '/static/images/razer-mouse.jpg', 'Razer DeathAdder V3 gaming mouse', 'Gaming', 'Razer');

-- Example of an order (existing)
-- INSERT INTO `order` (customer_id, total_amount, status) VALUES
-- (1, 1225.50, 'PENDING');

-- INSERT INTO order_item (order_id, product_id, quantity, price_at_order) VALUES
-- (1, 1, 1, 1200.00),
-- (1, 2, 1, 25.50);

-- Sample orders for ML Analytics - Creating diverse customer purchase patterns
-- High-value customer (Alice) - Recent and frequent purchases
INSERT INTO `order` (customer_id, total_amount, status, order_date) VALUES
(1, 2598.99, 'COMPLETED', '2025-07-15 10:30:00'),
(1, 149.99, 'COMPLETED', '2025-07-10 14:20:00'),
(1, 399.99, 'COMPLETED', '2025-07-05 09:15:00');

INSERT INTO order_item (order_id, product_id, quantity, price_at_order) VALUES
(1, 1, 1, 2499.00),  -- MacBook Pro
(1, 3, 1, 99.99),    -- Logitech Mouse
(2, 4, 1, 149.99),   -- Mechanical Keyboard
(3, 7, 1, 399.99);   -- Sony Headphones

-- Regular customer (Bob) - Moderate purchases
INSERT INTO `order` (customer_id, total_amount, status, order_date) VALUES
(2, 1298.99, 'COMPLETED', '2025-07-08 16:45:00'),
(2, 79.99, 'COMPLETED', '2025-06-20 11:30:00');

INSERT INTO order_item (order_id, product_id, quantity, price_at_order) VALUES
(4, 2, 1, 1299.00),  -- Dell XPS 13
(5, 10, 1, 79.99);   -- Razer Mouse

-- Budget-conscious customer (Charlie) - Lower value purchases
INSERT INTO `order` (customer_id, total_amount, status, order_date) VALUES
(3, 179.98, 'COMPLETED', '2025-06-15 13:20:00'),
(3, 99.99, 'COMPLETED', '2025-05-28 10:10:00');

INSERT INTO order_item (order_id, product_id, quantity, price_at_order) VALUES
(6, 3, 1, 99.99),    -- Logitech Mouse
(6, 10, 1, 79.99),   -- Razer Mouse
(7, 3, 1, 99.99);    -- Logitech Mouse

-- Premium customer (Diana) - High-value recent purchases
INSERT INTO `order` (customer_id, total_amount, status, order_date) VALUES
(4, 1998.00, 'COMPLETED', '2025-07-12 15:30:00'),
(4, 649.99, 'COMPLETED', '2025-07-02 12:45:00');

INSERT INTO order_item (order_id, product_id, quantity, price_at_order) VALUES
(8, 5, 2, 999.00),   -- iPhone 15 Pro x2
(9, 9, 1, 649.99);   -- ASUS Monitor

-- Tech enthusiast (Emma) - Diverse tech purchases
INSERT INTO `order` (customer_id, total_amount, status, order_date) VALUES
(5, 1798.00, 'COMPLETED', '2025-07-01 09:25:00'),
(5, 599.00, 'COMPLETED', '2025-06-10 14:15:00');

INSERT INTO order_item (order_id, product_id, quantity, price_at_order) VALUES
(10, 6, 1, 1199.00), -- Samsung Galaxy S24
(10, 8, 1, 599.00),  -- iPad Air
(11, 8, 1, 599.00);  -- iPad Air

-- Inactive customer (Frank) - Old purchases only
INSERT INTO `order` (customer_id, total_amount, status, order_date) VALUES
(6, 1548.99, 'COMPLETED', '2025-03-15 11:20:00'),
(6, 149.99, 'COMPLETED', '2025-02-20 16:30:00');

INSERT INTO order_item (order_id, product_id, quantity, price_at_order) VALUES
(12, 2, 1, 1299.00), -- Dell XPS 13
(12, 4, 1, 149.99),  -- Mechanical Keyboard
(12, 3, 1, 99.99),   -- Logitech Mouse
(13, 4, 1, 149.99);  -- Mechanical Keyboard

-- Frequent small purchases (Grace) - Multiple small orders
INSERT INTO `order` (customer_id, total_amount, status, order_date) VALUES
(7, 99.99, 'COMPLETED', '2025-07-14 08:15:00'),
(7, 79.99, 'COMPLETED', '2025-07-07 12:40:00'),
(7, 149.99, 'COMPLETED', '2025-06-25 15:20:00');

INSERT INTO order_item (order_id, product_id, quantity, price_at_order) VALUES
(14, 3, 1, 99.99),   -- Logitech Mouse
(15, 10, 1, 79.99),  -- Razer Mouse
(16, 4, 1, 149.99);  -- Mechanical Keyboard

-- New customer (Henry) - Single recent purchase
INSERT INTO `order` (customer_id, total_amount, status, order_date) VALUES
(8, 999.00, 'COMPLETED', '2025-07-18 10:00:00');

INSERT INTO order_item (order_id, product_id, quantity, price_at_order) VALUES
(17, 5, 1, 999.00);  -- iPhone 15 Pro

-- Mobile-focused customer (Iris) - Phone and accessories
INSERT INTO `order` (customer_id, total_amount, status, order_date) VALUES
(9, 1598.99, 'COMPLETED', '2025-07-03 13:25:00'),
(9, 399.99, 'COMPLETED', '2025-06-18 11:45:00');

INSERT INTO order_item (order_id, product_id, quantity, price_at_order) VALUES
(18, 6, 1, 1199.00), -- Samsung Galaxy S24
(18, 7, 1, 399.99),  -- Sony Headphones
(19, 7, 1, 399.99);  -- Sony Headphones

-- Potential churn customer (Jack) - No recent activity
INSERT INTO `order` (customer_id, total_amount, status, order_date) VALUES
(10, 2898.00, 'COMPLETED', '2025-01-15 14:30:00'),
(10, 599.00, 'COMPLETED', '2024-12-20 10:15:00');

INSERT INTO order_item (order_id, product_id, quantity, price_at_order) VALUES
(20, 1, 1, 2499.00), -- MacBook Pro
(20, 7, 1, 399.99),  -- Sony Headphones
(21, 8, 1, 599.00);  -- iPad Air

-- HIGH RISK CHURN CUSTOMER (Sarah) - Valuable customer who has gone inactive
-- Pattern: High initial spending, then declining activity, very old last purchase
INSERT INTO `order` (customer_id, total_amount, status, order_date) VALUES
(11, 3897.97, 'COMPLETED', '2024-08-15 10:30:00'),  -- 11+ months ago - HIGH RISK!
(11, 2199.00, 'COMPLETED', '2024-06-20 14:20:00'),  -- 13+ months ago
(11, 1798.99, 'COMPLETED', '2024-04-10 09:15:00'),  -- 15+ months ago
(11, 999.00, 'COMPLETED', '2024-02-05 11:45:00');   -- 17+ months ago

INSERT INTO order_item (order_id, product_id, quantity, price_at_order) VALUES
-- Most recent order (11+ months ago) - expensive items
(22, 1, 1, 2499.00),  -- MacBook Pro
(22, 6, 1, 1199.00),  -- Samsung Galaxy S24 
(22, 10, 2, 79.99),   -- Razer Mouse x2
(22, 3, 1, 99.99),    -- Logitech Mouse
-- Previous orders showing declining engagement
(23, 5, 2, 999.00),   -- iPhone 15 Pro x2 (older order)
(23, 7, 1, 399.99),   -- Sony Headphones
(24, 2, 1, 1299.00),  -- Dell XPS 13
(24, 9, 1, 649.99),   -- ASUS Monitor
(25, 5, 1, 999.00);   -- iPhone 15 Pro (oldest order)