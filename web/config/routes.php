<?php

use Slim\App;
use App\Controllers\HomeController;
use App\Controllers\CatalogController;
use App\Controllers\RecipeController;
use App\Controllers\PlanController;
use App\Controllers\HelpController;

use Slim\Routing\RouteCollectorProxy;
use App\Controllers\AuthController;
use App\Middleware\AuthMiddleware;

return function (App $app) {
    $container = $app->getContainer();

    // Routes
    $app->get('/', [HomeController::class, 'index']);
    $app->get('/help', [HelpController::class, 'index']);
    $app->get('/health', [HomeController::class, 'health']);

    // Auth Routes
    $app->get('/login', [AuthController::class, 'loginForm']);
    $app->post('/login', [AuthController::class, 'login']);
    $app->get('/register', [AuthController::class, 'registerForm']);
    $app->post('/register', [AuthController::class, 'register']);
    $app->get('/logout', [AuthController::class, 'logout']);

    // Google OAuth
    $app->get('/auth/google', [AuthController::class, 'googleLogin']);
    $app->get('/redirect', [AuthController::class, 'googleCallback']);

    // Recipe Routes (Moved to Protected)

    // Protected Routes
    $app->group('', function (RouteCollectorProxy $group) {
        // Plan Routes
        $group->get('/plans', [PlanController::class, 'index']);
        $group->get('/plans/new', [PlanController::class, 'create']);
        $group->post('/plans', [PlanController::class, 'store']);
        $group->get('/plans/{id}', [PlanController::class, 'show']);
        $group->post('/plans/{id}/grocery', [PlanController::class, 'generateGrocery']);
        $group->post('/plans/{id}/prep', [PlanController::class, 'generatePrep']);
        $group->post('/plans/{id}/swap', [PlanController::class, 'swap']);
        $group->post('/plans/{id}/remove', [PlanController::class, 'remove']);
        $group->post('/plans/{id}/add', [PlanController::class, 'add']);
        $group->post('/plans/{id}/share', [PlanController::class, 'toggleShare']);
        $group->post('/plans/{id}/like', [PlanController::class, 'toggleLike']);
        $group->post('/plans/{id}/update', [PlanController::class, 'update']);
        $group->post('/plans/{id}/delete', [PlanController::class, 'delete']);
        $group->post('/plans/{id}/clone', [PlanController::class, 'clone']);

        // Catalog Routes
        $group->get('/catalogs', [CatalogController::class, 'index']);
        $group->post('/catalogs/import', [CatalogController::class, 'import']);
        $group->get('/catalogs/{id}', [CatalogController::class, 'show']);
        $group->post('/catalogs/{id}', [CatalogController::class, 'update']);
        $group->post('/catalogs/{id}/delete', [CatalogController::class, 'delete']);

        // Recipe Protected Routes
        $group->get('/recipes', [RecipeController::class, 'index']);
        $group->get('/recipes/{id}[/]', [RecipeController::class, 'show']); // Allow optional trailing slash
        $group->get('/recipes/{id}/edit', [RecipeController::class, 'edit']);
        $group->post('/recipes/{id}', [RecipeController::class, 'update']);
        $group->post('/recipes/{id}/delete', [RecipeController::class, 'delete']);
    })->add(AuthMiddleware::class);
};
