-- Catalogs (cookbook sources)
CREATE TABLE catalogs (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    source_folder VARCHAR(500),
    model_used VARCHAR(100),
    recipe_count INT DEFAULT 0,
    metadata JSON,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

-- Chapters within catalogs
CREATE TABLE chapters (
    id INT AUTO_INCREMENT PRIMARY KEY,
    catalog_id INT NOT NULL,
    chapter_number VARCHAR(50),
    chapter_title VARCHAR(255),
    recipe_list JSON,
    FOREIGN KEY (catalog_id) REFERENCES catalogs(id) ON DELETE CASCADE
);

-- Recipes
CREATE TABLE recipes (
    id INT AUTO_INCREMENT PRIMARY KEY,
    catalog_id INT,
    name VARCHAR(255) NOT NULL,
    chapter VARCHAR(255),
    chapter_number VARCHAR(50),
    page_number VARCHAR(20),
    meal_type ENUM('breakfast', 'lunch', 'dinner', 'dessert', 'snack', 'main', 'side', 'any') DEFAULT 'any',
    dish_role ENUM('main', 'side', 'sub_recipe') DEFAULT 'main',
    serves VARCHAR(50),
    prep_time VARCHAR(50),
    cook_time VARCHAR(50),
    total_time VARCHAR(50),
    calories VARCHAR(20),
    protein VARCHAR(20),
    carbs VARCHAR(20),
    fat VARCHAR(20),
    nutrition_full TEXT,
    description TEXT,
    instructions JSON,
    tips JSON,
    sub_recipes JSON,
    dietary_info JSON,
    is_complete BOOLEAN DEFAULT TRUE,
    source_images JSON,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (catalog_id) REFERENCES catalogs(id) ON DELETE SET NULL,
    INDEX idx_meal_type (meal_type),
    INDEX idx_dish_role (dish_role),
    INDEX idx_name (name),
    FULLTEXT INDEX idx_search (name, description, chapter)
);

-- Ingredients (normalized for search)
CREATE TABLE ingredients (
    id INT AUTO_INCREMENT PRIMARY KEY,
    recipe_id INT NOT NULL,
    ingredient_text VARCHAR(500) NOT NULL,
    sort_order INT DEFAULT 0,
    FOREIGN KEY (recipe_id) REFERENCES recipes(id) ON DELETE CASCADE,
    INDEX idx_recipe (recipe_id)
);

-- Users (Authentication & RBAC)
CREATE TABLE users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(100) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NULL, -- Nullable for Google Auth users
    role VARCHAR(50) DEFAULT 'user',
    google_id VARCHAR(255) UNIQUE DEFAULT NULL,
    avatar_url VARCHAR(500) DEFAULT NULL,
    preferences JSON,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP
);

-- Meal Plans
CREATE TABLE meal_plans (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT,
    name VARCHAR(255),
    is_public BOOLEAN DEFAULT FALSE,
    meal_types JSON,
    recipe_count INT DEFAULT 5,
    target_servings INT DEFAULT 4,
    grocery_list JSON,
    prep_plan JSON,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_user (user_id),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL
);

-- Meal Plan Recipes (junction table)
CREATE TABLE meal_plan_recipes (
    id INT AUTO_INCREMENT PRIMARY KEY,
    plan_id INT NOT NULL,
    recipe_id INT NOT NULL,
    position INT DEFAULT 0,
    FOREIGN KEY (plan_id) REFERENCES meal_plans(id) ON DELETE CASCADE,
    FOREIGN KEY (recipe_id) REFERENCES recipes(id) ON DELETE CASCADE,
    INDEX idx_plan (plan_id)
);

-- Sessions
CREATE TABLE sessions (
    id VARCHAR(128) PRIMARY KEY,
    user_id INT,
    data TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- Plan Likes (Social Feature)
CREATE TABLE plan_likes (
    user_id INT NOT NULL,
    plan_id INT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (user_id, plan_id),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (plan_id) REFERENCES meal_plans(id) ON DELETE CASCADE
);
