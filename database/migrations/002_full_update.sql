-- 1. Update Users Table (Auth & RBAC)
-- If these fail because columns exist, you can ignore the specific error and move to the next line.
ALTER TABLE users ADD COLUMN role VARCHAR(50) DEFAULT 'user';
ALTER TABLE users ADD COLUMN google_id VARCHAR(255) UNIQUE DEFAULT NULL;
ALTER TABLE users ADD COLUMN avatar_url VARCHAR(500) DEFAULT NULL;
ALTER TABLE users ADD COLUMN preferences JSON;
ALTER TABLE users MODIFY COLUMN password_hash VARCHAR(255) NULL;

-- 2. Update Meal Plans Table (Community Features)
ALTER TABLE meal_plans ADD COLUMN is_public BOOLEAN DEFAULT FALSE;

-- 3. Create Plan Likes Table (Community Features)
CREATE TABLE IF NOT EXISTS plan_likes (
    user_id INT NOT NULL,
    plan_id INT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (user_id, plan_id),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (plan_id) REFERENCES meal_plans(id) ON DELETE CASCADE
);
