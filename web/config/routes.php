<?php

declare(strict_types=1);

use Slim\App;
use MealPlanner\Controllers\HomeController;
use MealPlanner\Controllers\RecipeController;
use MealPlanner\Controllers\PlanController;
use MealPlanner\Controllers\CatalogController;
use MealPlanner\Controllers\AuthController;

return function (App $app) {
    // ==========================================
    // Authentication (public)
    // ==========================================
    $app->get('/login', [AuthController::class, 'loginForm'])->setName('auth.login');
    $app->post('/login', [AuthController::class, 'login'])->setName('auth.login.post');
    $app->get('/register', [AuthController::class, 'registerForm'])->setName('auth.register');
    $app->post('/register', [AuthController::class, 'register'])->setName('auth.register.post');
    $app->get('/logout', [AuthController::class, 'logout'])->setName('auth.logout');

    // ==========================================
    // Public Routes
    // ==========================================

    // Home / Dashboard
    $app->get('/', [HomeController::class, 'index'])->setName('home');

    // Recipes (public browsing)
    $app->get('/recipes', [RecipeController::class, 'index'])->setName('recipes.index');
    $app->get('/recipes/{id:[0-9]+}', [RecipeController::class, 'show'])->setName('recipes.show');
    $app->get('/recipes/search', [RecipeController::class, 'search'])->setName('recipes.search');

    // ==========================================
    // Meal Plans (works with or without auth)
    // ==========================================
    $app->get('/plans', [PlanController::class, 'index'])->setName('plans.index');
    $app->get('/plans/new', [PlanController::class, 'create'])->setName('plans.create');
    $app->post('/plans/generate', [PlanController::class, 'generate'])->setName('plans.generate');
    $app->get('/plans/{id:[0-9]+}', [PlanController::class, 'show'])->setName('plans.show');
    $app->delete('/plans/{id:[0-9]+}', [PlanController::class, 'delete'])->setName('plans.delete');
    $app->get('/plans/{id:[0-9]+}/grocery', [PlanController::class, 'grocery'])->setName('plans.grocery');
    $app->get('/plans/{id:[0-9]+}/prep', [PlanController::class, 'prep'])->setName('plans.prep');
    $app->post('/plans/{id:[0-9]+}/reroll/{recipeId:[0-9]+}', [PlanController::class, 'reroll'])->setName('plans.reroll');

    // ==========================================
    // Catalogs (admin functionality)
    // ==========================================
    $app->get('/catalogs', [CatalogController::class, 'index'])->setName('catalogs.index');
    $app->post('/catalogs/import', [CatalogController::class, 'import'])->setName('catalogs.import');
};
