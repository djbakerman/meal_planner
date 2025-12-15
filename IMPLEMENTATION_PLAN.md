# Meal Planner Web Interface - Implementation Plan

## Technical Stack (Confirmed)

| Layer | Technology | Version |
|-------|------------|---------|
| **PHP Framework** | Slim Framework | 4.x |
| **Database** | MariaDB | 10.x+ |
| **Python API** | FastAPI | 0.100+ |
| **Frontend** | Bootstrap 5 + HTMX | 5.3 / 1.9 |
| **Authentication** | Session-based (PHP sessions) | - |
| **Deployment** | Traditional LAMP | Apache 2.4+ |
| **PHP Version** | 8.2+ | Required |

## Design Philosophy: MVP First

- **Minimal UI**: Text-focused, no recipe images
- **Functional**: Core features working end-to-end
- **Clean**: Simple Bootstrap styling, no custom CSS initially
- **Fast**: Server-rendered pages with HTMX enhancements

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                   Browser (HTMX)                            │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│              Apache + PHP 8.2 (Slim 4)                      │
│                                                             │
│  /                    → Dashboard                           │
│  /recipes             → Recipe Browser                      │
│  /recipes/{id}        → Recipe Detail                       │
│  /plans               → Meal Plans List                     │
│  /plans/new           → Generate Plan                       │
│  /plans/{id}          → Plan Detail                         │
│  /plans/{id}/grocery  → Grocery List                        │
│  /plans/{id}/prep     → Prep Plan                           │
│  /catalogs            → Catalog Management                  │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                 FastAPI (Python)                            │
│                 localhost:8000                              │
│                                                             │
│  GET  /api/recipes              → List recipes              │
│  GET  /api/recipes/{id}         → Single recipe             │
│  POST /api/recipes/search       → Search/filter             │
│  GET  /api/recipes/random       → Random selection          │
│  POST /api/plans/generate       → Generate meal plan        │
│  POST /api/plans/{id}/grocery   → AI grocery list           │
│  POST /api/plans/{id}/prep      → AI prep plan              │
│  GET  /api/catalogs             → List catalogs             │
│  POST /api/catalogs/import      → Import JSON catalog       │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                      MariaDB                                │
│                                                             │
│  recipes, ingredients, catalogs, meal_plans, users          │
└─────────────────────────────────────────────────────────────┘
```

---

## Directory Structure

```
/home/user/meal_planner/
├── api/                          # FastAPI Python backend
│   ├── main.py                   # FastAPI app entry point
│   ├── routers/
│   │   ├── recipes.py
│   │   ├── plans.py
│   │   └── catalogs.py
│   ├── services/
│   │   ├── recipe_service.py     # Wraps existing Python logic
│   │   ├── plan_service.py
│   │   └── ai_service.py         # Ollama/Claude integration
│   ├── models/
│   │   └── schemas.py            # Pydantic models
│   ├── database.py               # SQLAlchemy connection
│   └── requirements.txt
│
├── web/                          # Slim PHP frontend
│   ├── public/
│   │   ├── index.php             # Entry point
│   │   └── assets/
│   │       ├── css/
│   │       │   └── app.css       # Minimal custom styles
│   │       └── js/
│   │           └── app.js        # HTMX config only
│   ├── src/
│   │   ├── Controllers/
│   │   │   ├── HomeController.php
│   │   │   ├── RecipeController.php
│   │   │   ├── PlanController.php
│   │   │   └── CatalogController.php
│   │   ├── Services/
│   │   │   ├── ApiClient.php     # FastAPI HTTP client
│   │   │   └── SessionService.php
│   │   ├── Middleware/
│   │   │   └── AuthMiddleware.php
│   │   └── helpers.php
│   ├── templates/
│   │   ├── layouts/
│   │   │   └── base.php          # Main layout
│   │   ├── home/
│   │   │   └── index.php         # Dashboard
│   │   ├── recipes/
│   │   │   ├── index.php         # List view
│   │   │   ├── show.php          # Detail view
│   │   │   └── _card.php         # Partial for HTMX
│   │   ├── plans/
│   │   │   ├── index.php         # Plans list
│   │   │   ├── show.php          # Plan detail
│   │   │   ├── new.php           # Generate form
│   │   │   ├── grocery.php       # Grocery list
│   │   │   └── prep.php          # Prep plan
│   │   ├── catalogs/
│   │   │   └── index.php
│   │   └── partials/
│   │       ├── _nav.php
│   │       ├── _flash.php
│   │       └── _pagination.php
│   ├── config/
│   │   ├── settings.php
│   │   └── routes.php
│   ├── composer.json
│   └── .htaccess
│
├── database/
│   ├── schema.sql                # MariaDB schema
│   └── seed.sql                  # Optional test data
│
├── scripts/
│   ├── import_catalog.py         # Migrate JSON → MariaDB
│   └── setup.sh                  # Environment setup
│
├── meal_planner.py               # Existing CLI tool
├── recipe_cataloger.py           # Existing CLI tool
├── page_analyzer.py              # Existing CLI tool
└── IMPLEMENTATION_PLAN.md        # This file
```

---

## Database Schema (MariaDB)

```sql
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

-- Meal Plans
CREATE TABLE meal_plans (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT,
    name VARCHAR(255),
    meal_types JSON,
    recipe_count INT DEFAULT 5,
    grocery_list JSON,
    prep_plan JSON,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_user (user_id)
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

-- Users (simple session auth)
CREATE TABLE users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(100) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    preferences JSON,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP
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
```

---

## Module Breakdown

### Module 1: Foundation Setup
**Goal**: Project scaffolding, database, basic routing

**Tasks**:
1. Create directory structure (`/api`, `/web`, `/database`)
2. Initialize Composer project for Slim 4
3. Set up FastAPI project with virtual environment
4. Create MariaDB database and run schema
5. Configure Apache virtual host / .htaccess
6. Create base PHP layout template
7. Set up HTMX + Bootstrap 5 CDN links
8. Create FastAPI health check endpoint
9. Create PHP ApiClient service class
10. Test end-to-end connectivity

**Files**:
- `web/composer.json`
- `web/public/index.php`
- `web/config/settings.php`
- `web/config/routes.php`
- `web/templates/layouts/base.php`
- `api/main.py`
- `api/requirements.txt`
- `database/schema.sql`

---

### Module 2: Catalog Import & Recipe Storage
**Goal**: Import existing JSON catalogs into MariaDB

**Tasks**:
1. Create Python import script (`scripts/import_catalog.py`)
2. Parse JSON catalog structure
3. Insert catalogs, chapters, recipes, ingredients
4. Handle sub-recipes and dietary tags
5. Create FastAPI `/api/catalogs` endpoints
6. Create PHP Catalog controller and views
7. Add "Import Catalog" form (file path input)
8. Display import results/stats

**Endpoints**:
- `GET /api/catalogs` - List all catalogs
- `POST /api/catalogs/import` - Import from JSON file path
- `GET /api/catalogs/{id}` - Catalog details with stats

---

### Module 3: Recipe Browser
**Goal**: Browse, search, and view recipes

**Tasks**:
1. Create FastAPI recipe endpoints
2. Implement pagination (20 per page)
3. Implement search (FULLTEXT on name, description)
4. Implement filters (meal_type, dish_role, dietary)
5. Create PHP RecipeController
6. Create recipe list view (table format, minimal)
7. Create recipe detail view
8. Add HTMX for filter/search without full reload
9. Add pagination with HTMX

**Endpoints**:
- `GET /api/recipes?page=1&limit=20` - Paginated list
- `GET /api/recipes/{id}` - Single recipe
- `POST /api/recipes/search` - Search with filters
- `GET /api/recipes/random?count=5&meal_type=dinner` - Random selection

**Views**:
- `/recipes` - Table list with filters sidebar
- `/recipes/{id}` - Full recipe details (text only)

---

### Module 4: Meal Plan Generation
**Goal**: Generate, save, and manage meal plans

**Tasks**:
1. Create FastAPI plan generation endpoint (wraps existing logic)
2. Create meal_plans and meal_plan_recipes DB operations
3. Create PHP PlanController
4. Create "New Plan" form (meal types, count)
5. Create plan list view
6. Create plan detail view (list of recipes)
7. Add "Reroll" button for individual recipes (HTMX)
8. Add "Save Plan" functionality
9. Add "Delete Plan" functionality

**Endpoints**:
- `GET /api/plans` - List saved plans
- `POST /api/plans/generate` - Generate new plan
- `GET /api/plans/{id}` - Plan details with recipes
- `PUT /api/plans/{id}` - Update plan
- `DELETE /api/plans/{id}` - Delete plan
- `POST /api/plans/{id}/reroll/{recipe_id}` - Replace one recipe

**Views**:
- `/plans` - List of saved plans
- `/plans/new` - Generation form
- `/plans/{id}` - Plan detail with recipe list

---

### Module 5: Grocery List & Prep Plan
**Goal**: AI-generated grocery lists and prep plans

**Tasks**:
1. Integrate existing AI logic into FastAPI
2. Create grocery list endpoint (calls Ollama/Claude)
3. Create prep plan endpoint
4. Cache generated lists in meal_plans table
5. Create PHP grocery list view
6. Create PHP prep plan view
7. Add print-friendly CSS
8. Add regenerate button

**Endpoints**:
- `POST /api/plans/{id}/grocery` - Generate/retrieve grocery list
- `POST /api/plans/{id}/prep` - Generate/retrieve prep plan

**Views**:
- `/plans/{id}/grocery` - Categorized grocery list
- `/plans/{id}/prep` - Timeline prep plan

---

### Module 6: Authentication (Simple)
**Goal**: Basic user login/logout for session persistence

**Tasks**:
1. Create login/register forms
2. Create AuthMiddleware for protected routes
3. Password hashing with PHP password_hash()
4. Session management
5. User preferences storage
6. Associate meal plans with users

**Views**:
- `/login` - Login form
- `/register` - Registration form
- `/logout` - Logout action

---

## Implementation Order

```
Module 1: Foundation Setup
    │
    ▼
Module 2: Catalog Import
    │
    ▼
Module 3: Recipe Browser  ◄── MVP Checkpoint 1 (read-only browsing)
    │
    ▼
Module 4: Meal Plan Generation  ◄── MVP Checkpoint 2 (core functionality)
    │
    ▼
Module 5: Grocery & Prep  ◄── MVP Checkpoint 3 (AI features)
    │
    ▼
Module 6: Authentication  ◄── MVP Checkpoint 4 (multi-user ready)
```

---

## MVP Feature Matrix

| Feature | MVP v1 | Future |
|---------|--------|--------|
| Recipe browsing | ✅ Table list | Grid with images |
| Recipe search | ✅ Name search | Full-text + ingredients |
| Recipe filters | ✅ Meal type, role | Calories, prep time |
| Recipe detail | ✅ Text only | Images, print layout |
| Meal plan generate | ✅ Basic random | Calendar view |
| Meal plan save | ✅ Simple save | Named plans, sharing |
| Reroll recipe | ✅ Single swap | Drag-drop reorder |
| Grocery list | ✅ AI consolidated | Checkbox, export |
| Prep plan | ✅ Timeline text | Visual timeline |
| Authentication | ✅ Login/register | OAuth, API keys |
| Catalog import | ✅ JSON file path | Upload images |
| Recipe images | ❌ | Future version |
| Dark mode | ❌ | Future version |
| Mobile app | ❌ | Future version |

---

## File Dependencies

```
Module 1 creates:
├── web/public/index.php
├── web/composer.json
├── web/config/settings.php
├── web/config/routes.php
├── web/templates/layouts/base.php
├── web/src/Services/ApiClient.php
├── api/main.py
├── api/requirements.txt
├── api/database.py
└── database/schema.sql

Module 2 requires Module 1, creates:
├── scripts/import_catalog.py
├── api/routers/catalogs.py
├── api/services/catalog_service.py
├── web/src/Controllers/CatalogController.php
└── web/templates/catalogs/index.php

Module 3 requires Module 2, creates:
├── api/routers/recipes.py
├── api/services/recipe_service.py
├── web/src/Controllers/RecipeController.php
├── web/templates/recipes/index.php
├── web/templates/recipes/show.php
└── web/templates/partials/_pagination.php

Module 4 requires Module 3, creates:
├── api/routers/plans.py
├── api/services/plan_service.py
├── web/src/Controllers/PlanController.php
├── web/templates/plans/index.php
├── web/templates/plans/new.php
└── web/templates/plans/show.php

Module 5 requires Module 4, creates:
├── api/services/ai_service.py
├── web/templates/plans/grocery.php
└── web/templates/plans/prep.php

Module 6 requires Module 1, creates:
├── web/src/Controllers/AuthController.php
├── web/src/Middleware/AuthMiddleware.php
├── web/templates/auth/login.php
└── web/templates/auth/register.php
```

---

## Ready to Implement

Confirm this plan and I will begin with **Module 1: Foundation Setup**, which includes:

1. Creating the directory structure
2. Setting up Slim 4 PHP project with Composer
3. Setting up FastAPI Python project
4. Creating the MariaDB schema
5. Building the base layout template
6. Establishing API connectivity

Shall I proceed?
