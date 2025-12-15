-- Meal Planner Database Schema
-- MariaDB 10.x+

-- Create database if not exists
CREATE DATABASE IF NOT EXISTS meal_planner
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;

USE meal_planner;

-- ============================================
-- Catalogs (cookbook sources)
-- ============================================
CREATE TABLE IF NOT EXISTS catalogs (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    source_folder VARCHAR(500),
    model_used VARCHAR(100),
    recipe_count INT DEFAULT 0,
    metadata JSON,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB;

-- ============================================
-- Chapters within catalogs
-- ============================================
CREATE TABLE IF NOT EXISTS chapters (
    id INT AUTO_INCREMENT PRIMARY KEY,
    catalog_id INT NOT NULL,
    chapter_number VARCHAR(50),
    chapter_title VARCHAR(255),
    recipe_list JSON,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (catalog_id) REFERENCES catalogs(id) ON DELETE CASCADE,
    INDEX idx_catalog (catalog_id)
) ENGINE=InnoDB;

-- ============================================
-- Recipes
-- ============================================
CREATE TABLE IF NOT EXISTS recipes (
    id INT AUTO_INCREMENT PRIMARY KEY,
    catalog_id INT,
    name VARCHAR(255) NOT NULL,
    chapter VARCHAR(255),
    chapter_number VARCHAR(50),
    page_number VARCHAR(20),
    meal_type ENUM('breakfast', 'lunch', 'dinner', 'dessert', 'snack', 'any') DEFAULT 'any',
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
    INDEX idx_catalog (catalog_id),
    INDEX idx_name (name),
    FULLTEXT INDEX idx_search (name, description, chapter)
) ENGINE=InnoDB;

-- ============================================
-- Ingredients (normalized for search)
-- ============================================
CREATE TABLE IF NOT EXISTS ingredients (
    id INT AUTO_INCREMENT PRIMARY KEY,
    recipe_id INT NOT NULL,
    ingredient_text VARCHAR(500) NOT NULL,
    sort_order INT DEFAULT 0,
    FOREIGN KEY (recipe_id) REFERENCES recipes(id) ON DELETE CASCADE,
    INDEX idx_recipe (recipe_id)
) ENGINE=InnoDB;

-- ============================================
-- Users (simple session auth)
-- ============================================
CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(100) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    preferences JSON,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP NULL,
    INDEX idx_email (email),
    INDEX idx_username (username)
) ENGINE=InnoDB;

-- ============================================
-- Meal Plans
-- ============================================
CREATE TABLE IF NOT EXISTS meal_plans (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT,
    name VARCHAR(255),
    meal_types JSON,
    recipe_count INT DEFAULT 5,
    grocery_list JSON,
    prep_plan JSON,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL,
    INDEX idx_user (user_id)
) ENGINE=InnoDB;

-- ============================================
-- Meal Plan Recipes (junction table)
-- ============================================
CREATE TABLE IF NOT EXISTS meal_plan_recipes (
    id INT AUTO_INCREMENT PRIMARY KEY,
    plan_id INT NOT NULL,
    recipe_id INT NOT NULL,
    position INT DEFAULT 0,
    FOREIGN KEY (plan_id) REFERENCES meal_plans(id) ON DELETE CASCADE,
    FOREIGN KEY (recipe_id) REFERENCES recipes(id) ON DELETE CASCADE,
    INDEX idx_plan (plan_id),
    INDEX idx_recipe (recipe_id)
) ENGINE=InnoDB;

-- ============================================
-- Sessions (PHP session storage)
-- ============================================
CREATE TABLE IF NOT EXISTS sessions (
    id VARCHAR(128) PRIMARY KEY,
    user_id INT,
    data TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP NULL,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    INDEX idx_user (user_id),
    INDEX idx_expires (expires_at)
) ENGINE=InnoDB;

-- ============================================
-- Processing Logs (for catalog imports)
-- ============================================
CREATE TABLE IF NOT EXISTS processing_logs (
    id INT AUTO_INCREMENT PRIMARY KEY,
    catalog_id INT NOT NULL,
    file_name VARCHAR(255),
    status ENUM('success', 'skipped', 'error') DEFAULT 'success',
    page_type VARCHAR(50),
    recipes_extracted JSON,
    diagnostic JSON,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (catalog_id) REFERENCES catalogs(id) ON DELETE CASCADE,
    INDEX idx_catalog (catalog_id)
) ENGINE=InnoDB;
