<?php

declare(strict_types=1);

namespace MealPlanner\Controllers;

use MealPlanner\Services\ApiClient;
use Psr\Http\Message\ResponseInterface as Response;
use Psr\Http\Message\ServerRequestInterface as Request;
use Slim\Views\PhpRenderer;

class RecipeController
{
    public function __construct(
        private PhpRenderer $view,
        private ApiClient $apiClient
    ) {}

    /**
     * List all recipes with pagination and filters
     */
    public function index(Request $request, Response $response): Response
    {
        $params = $request->getQueryParams();
        $page = (int) ($params['page'] ?? 1);
        $mealType = $params['meal_type'] ?? null;
        $dishRole = $params['dish_role'] ?? null;

        $query = ['page' => $page, 'limit' => 20];
        if ($mealType) $query['meal_type'] = $mealType;
        if ($dishRole) $query['dish_role'] = $dishRole;

        $result = $this->apiClient->get('api/recipes', $query);

        return $this->view->render($response, 'recipes/index.php', [
            'title' => 'Recipes - Meal Planner',
            'activeNav' => 'recipes',
            'recipes' => $result['recipes'] ?? [],
            'pagination' => $result['pagination'] ?? [],
            'filters' => [
                'meal_type' => $mealType,
                'dish_role' => $dishRole,
            ],
        ]);
    }

    /**
     * Show single recipe details
     */
    public function show(Request $request, Response $response, array $args): Response
    {
        $id = (int) $args['id'];
        $recipe = $this->apiClient->get("api/recipes/{$id}");

        if (isset($recipe['error'])) {
            // Recipe not found, redirect to list
            return $response->withHeader('Location', '/recipes')->withStatus(302);
        }

        return $this->view->render($response, 'recipes/show.php', [
            'title' => ($recipe['name'] ?? 'Recipe') . ' - Meal Planner',
            'activeNav' => 'recipes',
            'recipe' => $recipe,
        ]);
    }

    /**
     * Search recipes (HTMX partial response)
     */
    public function search(Request $request, Response $response): Response
    {
        $params = $request->getQueryParams();
        $query = $params['q'] ?? '';

        $result = $this->apiClient->post('api/recipes/search', [
            'query' => $query,
            'limit' => 20,
        ]);

        // Check if this is an HTMX request
        $isHtmx = $request->hasHeader('HX-Request');

        if ($isHtmx) {
            // Return partial HTML for HTMX
            return $this->view->render($response, 'recipes/_list.php', [
                'recipes' => $result['recipes'] ?? [],
            ]);
        }

        // Full page response
        return $this->view->render($response, 'recipes/index.php', [
            'title' => 'Search Results - Meal Planner',
            'activeNav' => 'recipes',
            'recipes' => $result['recipes'] ?? [],
            'searchQuery' => $query,
        ]);
    }
}
