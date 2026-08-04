-- Sample rows for the Chat-with-Database demo dataset.
-- Runs after 001_schema.sql via docker-entrypoint-initdb.d.

INSERT INTO customers (name, email, state, signup_date) VALUES
    ('Alice Chen', 'alice.chen@example.com', 'CA', '2024-01-15'),
    ('Marcus Reed', 'marcus.reed@example.com', 'NY', '2024-02-03'),
    ('Priya Nair', 'priya.nair@example.com', 'CA', '2024-02-20'),
    ('Diego Alvarez', 'diego.alvarez@example.com', 'TX', '2024-03-11'),
    ('Sofia Rossi', 'sofia.rossi@example.com', 'CA', '2024-04-02'),
    ('James Whitfield', 'james.whitfield@example.com', 'WA', '2024-04-19'),
    ('Hana Kobayashi', 'hana.kobayashi@example.com', 'NY', '2024-05-07'),
    ('Omar Farouk', 'omar.farouk@example.com', 'TX', '2024-06-01');

INSERT INTO products (name, category, price) VALUES
    ('Wireless Mouse', 'Electronics', 24.99),
    ('Mechanical Keyboard', 'Electronics', 89.99),
    ('USB-C Hub', 'Electronics', 39.99),
    ('Ceramic Coffee Mug', 'Home', 14.50),
    ('Standing Desk Mat', 'Home', 45.00),
    ('Notebook (3-pack)', 'Office', 12.99),
    ('Desk Lamp', 'Home', 32.00),
    ('Noise-Cancelling Headphones', 'Electronics', 149.99);

INSERT INTO orders (customer_id, status, total, created_at) VALUES
    (1, 'delivered', 64.98, '2024-05-01T10:00:00Z'),
    (1, 'shipped', 149.99, '2024-06-10T14:30:00Z'),
    (2, 'delivered', 39.99, '2024-05-15T09:15:00Z'),
    (3, 'pending', 45.00, '2024-06-20T16:45:00Z'),
    (4, 'delivered', 102.49, '2024-05-22T11:20:00Z'),
    (5, 'cancelled', 32.00, '2024-05-28T13:00:00Z'),
    (6, 'delivered', 89.99, '2024-06-02T08:40:00Z'),
    (7, 'shipped', 27.49, '2024-06-15T17:10:00Z'),
    (3, 'delivered', 149.99, '2024-06-25T12:00:00Z'),
    (8, 'delivered', 14.50, '2024-06-28T19:30:00Z');

INSERT INTO order_items (order_id, product_id, quantity, unit_price) VALUES
    (1, 1, 1, 24.99),
    (1, 4, 1, 14.50),
    (1, 6, 2, 12.99),
    (2, 8, 1, 149.99),
    (3, 3, 1, 39.99),
    (4, 5, 1, 45.00),
    (5, 2, 1, 89.99),
    (5, 4, 1, 14.50),
    (6, 7, 1, 32.00),
    (7, 2, 1, 89.99),
    (8, 6, 1, 12.99),
    (8, 4, 1, 14.50),
    (9, 8, 1, 149.99),
    (10, 4, 1, 14.50);

INSERT INTO reviews (product_id, customer_id, rating, comment, created_at) VALUES
    (1, 1, 5, 'Smooth tracking, great battery life.', '2024-05-05T10:00:00Z'),
    (8, 1, 4, 'Sound quality is excellent, a bit tight on the ears.', '2024-06-14T09:00:00Z'),
    (3, 2, 5, 'Works with all my devices, very sturdy.', '2024-05-18T12:00:00Z'),
    (2, 6, 5, 'Best keyboard I have owned, satisfying switches.', '2024-06-05T15:00:00Z'),
    (8, 3, 5, 'Noise cancellation is fantastic for the office.', '2024-06-27T10:30:00Z'),
    (7, 5, 2, 'Arrived with a flickering bulb, had to return.', '2024-06-01T08:00:00Z'),
    (4, 8, 4, 'Simple and does the job, good size.', '2024-06-29T11:00:00Z');
