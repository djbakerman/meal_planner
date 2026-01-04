<?php

namespace App\Controllers;

use Psr\Http\Message\ResponseInterface as Response;
use Psr\Http\Message\ServerRequestInterface as Request;
use Slim\Views\PhpRenderer;
use App\Services\ApiClient;

use App\Services\SessionService;

class RecipeController
{
    protected $view;
    protected $api;
    protected $session;

    public function __construct(PhpRenderer $view, ApiClient $api, SessionService $session)
    {
        $this->view = $view;
        $this->api = $api;
        $this->session = $session;
    }

    public function index(Request $request, Response $response, $args): Response
    {
        $queryParams = $request->getQueryParams();
        $page = $queryParams['page'] ?? 1;
        $limit = 50;  // Increased for better visibility
        $skip = ($page - 1) * $limit;

        $filters = [
            'skip' => $skip,
            'limit' => $limit
        ];

        if (!empty($queryParams['search'])) {
            $filters['search'] = $queryParams['search'];
        }
        if (!empty($queryParams['meal_type']) && $queryParams['meal_type'] !== 'all') {
            $filters['meal_type'] = $queryParams['meal_type'];
        }
        if (!empty($queryParams['dish_role']) && $queryParams['dish_role'] !== 'all') {
            $filters['dish_role'] = $queryParams['dish_role'];
        }
        if (!empty($queryParams['catalog_id'])) {
            $filters['catalog_id'] = $queryParams['catalog_id'];
        }

        // Fetch recipes from API
        $recipes = $this->api->get('/api/recipes', $filters);

        // Fetch catalogs for filter
        $catalogs = $this->api->get('/api/catalogs/');

        // Get total count for pagination (simplified for now, ideally API returns metadata)
        // For MVP, we might just check if we got full limit to determine "Next"
        $countData = $this->api->get('/api/recipes/count');
        $total = $countData['count'] ?? 0;
        $totalPages = ceil($total / $limit);

        error_log("Pagination Debug: Total=$total, Limit=$limit, Pages=$totalPages");

        $this->view->setLayout('layouts/main.php');
        return $this->view->render($response, 'recipes/index.php', [
            'title' => 'Browse Recipes',
            'recipes' => $recipes,
            'catalogs' => $catalogs,
            'currentPage' => (int) $page,
            'totalPages' => $totalPages,
            'filters' => $queryParams,
            'totalRecipes' => $total
        ]);
    }

    public function show(Request $request, Response $response, $args): Response
    {
        $id = $args['id'];
        $recipe = $this->api->get("/api/recipes/{$id}");

        if (!$recipe || isset($recipe['detail'])) {
            // Handle 404
            $response->getBody()->write("Recipe not found");
            return $response->withStatus(404);
        }

        // Fetch Ingredient Density Map
        $densityData = $this->api->get('/api/ingredients/density');

        $this->view->setLayout('layouts/main.php');
        return $this->view->render($response, 'recipes/show.php', [
            'title' => $recipe['name'],
            'recipe' => $recipe,
            'densityData' => $densityData, // Pass to view
            'queryParams' => $request->getQueryParams()
        ]);
    }

    public function edit(Request $request, Response $response, $args): Response
    {
        $id = $args['id'];
        $recipe = $this->api->get("/api/recipes/{$id}");

        if (!$recipe || isset($recipe['detail'])) {
            $this->session->flash('error', 'Recipe not found.');
            return $response->withHeader('Location', '/recipes')->withStatus(302);
        }

        $this->view->setLayout('layouts/main.php');
        return $this->view->render($response, 'recipes/edit.php', [
            'title' => 'Edit ' . $recipe['name'],
            'recipe' => $recipe,
            'flash' => $this->session->getFlash()
        ]);
    }

    public function update(Request $request, Response $response, $args): Response
    {
        $id = $args['id'];
        $data = $request->getParsedBody();

        $this->api->put("/api/recipes/{$id}", $data);
        $this->session->flash('success', 'Recipe updated.');

        return $response->withHeader('Location', "/recipes/{$id}")->withStatus(302);
    }

    public function delete(Request $request, Response $response, $args): Response
    {
        $id = $args['id'];
        $this->api->delete("/api/recipes/{$id}");
        $this->session->flash('success', 'Recipe deleted.');

        return $response->withHeader('Location', '/recipes')->withStatus(302);
    }
}
