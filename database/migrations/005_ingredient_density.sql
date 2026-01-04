CREATE TABLE ingredient_density (
    ingredient_key VARCHAR(255) PRIMARY KEY, -- Normalized key e.g. "flow_all_purpose"
    display_name VARCHAR(255),
    density_g_per_ml DOUBLE,
    confidence_level VARCHAR(50) DEFAULT 'medium',
    source VARCHAR(255),
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Seed Data (Ref: User provided list)
INSERT INTO ingredient_density (ingredient_key, display_name, density_g_per_ml, confidence_level, notes) VALUES
('flour_all_purpose', 'All-purpose flour', 0.53, 'high', 'Sifted'),
('flour_bread', 'Bread flour', 0.57, 'medium', ''),
('sugar_granulated', 'Granulated sugar', 0.85, 'high', ''),
('sugar_brown', 'Brown sugar (packed)', 0.93, 'high', 'Packed'),
('sugar_powdered', 'Powdered sugar', 0.56, 'medium', ''),
('salt_table', 'Salt (table)', 1.20, 'high', ''),
('baking_soda', 'Baking soda', 0.69, 'high', ''),
('baking_powder', 'Baking powder', 0.90, 'high', ''),
('cocoa_powder', 'Cocoa powder', 0.45, 'medium', ''),
('water', 'Water', 1.00, 'high', ''),
('milk', 'Milk', 1.03, 'high', ''),
('cream_heavy', 'Heavy cream', 0.99, 'high', ''),
('oil_olive', 'Olive oil', 0.91, 'high', ''),
('oil_vegetable', 'Vegetable oil', 0.92, 'high', ''),
('butter', 'Butter', 0.91, 'high', 'Solid/Melted avg'),
('honey', 'Honey', 1.42, 'high', ''),
('syrup_maple', 'Maple syrup', 1.33, 'high', ''),
('rice_uncooked', 'Rice (uncooked)', 0.85, 'medium', ''),
('oats_rolled', 'Oats (rolled)', 0.41, 'high', ''),
('peanut_butter', 'Peanut butter', 1.06, 'high', ''),
('yogurt', 'Yogurt', 1.03, 'high', ''),
('paste_tomato', 'Tomato paste', 1.09, 'medium', ''),
('cheese_grated', 'Grated cheese', 0.40, 'low', 'Varies by shred');
