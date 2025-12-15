<?php

declare(strict_types=1);

namespace MealPlanner\Controllers;

use MealPlanner\Services\ApiClient;
use Psr\Http\Message\ResponseInterface as Response;
use Psr\Http\Message\ServerRequestInterface as Request;
use Slim\Views\PhpRenderer;

class PlanController
{
    public function __construct(
        private PhpRenderer $view,
        private ApiClient $apiClient
    ) {}

    /**
     * List all meal plans
     */
    public function index(Request $request, Response $response): Response
    {
        $result = $this->apiClient->get('api/plans');

        return $this->view->render($response, 'plans/index.php', [
            'title' => 'Meal Plans - Meal Planner',
            'activeNav' => 'plans',
            'plans' => $result['plans'] ?? [],
        ]);
    }

    /**
     * Show create plan form
     */
    public function create(Request $request, Response $response): Response
    {
        return $this->view->render($response, 'plans/new.php', [
            'title' => 'New Meal Plan - Meal Planner',
            'activeNav' => 'plans',
        ]);
    }

    /**
     * Generate a new meal plan
     */
    public function generate(Request $request, Response $response): Response
    {
        $data = $request->getParsedBody();

        $result = $this->apiClient->post('api/plans/generate', [
            'meal_types' => $data['meal_types'] ?? ['dinner'],
            'count' => (int) ($data['count'] ?? 5),
            'name' => $data['name'] ?? null,
        ]);

        if (isset($result['error'])) {
            // Handle error - redirect back with flash message
            return $response->withHeader('Location', '/plans/new')->withStatus(302);
        }

        $planId = $result['id'] ?? 0;
        return $response->withHeader('Location', "/plans/{$planId}")->withStatus(302);
    }

    /**
     * Show single meal plan
     */
    public function show(Request $request, Response $response, array $args): Response
    {
        $id = (int) $args['id'];
        $plan = $this->apiClient->get("api/plans/{$id}");

        if (isset($plan['error'])) {
            return $response->withHeader('Location', '/plans')->withStatus(302);
        }

        return $this->view->render($response, 'plans/show.php', [
            'title' => ($plan['name'] ?? 'Meal Plan') . ' - Meal Planner',
            'activeNav' => 'plans',
            'plan' => $plan,
        ]);
    }

    /**
     * Delete a meal plan
     */
    public function delete(Request $request, Response $response, array $args): Response
    {
        $id = (int) $args['id'];
        $this->apiClient->delete("api/plans/{$id}");

        return $response->withHeader('Location', '/plans')->withStatus(302);
    }

    /**
     * Show grocery list for a plan
     */
    public function grocery(Request $request, Response $response, array $args): Response
    {
        $id = (int) $args['id'];
        $result = $this->apiClient->post("api/plans/{$id}/grocery", []);

        return $this->view->render($response, 'plans/grocery.php', [
            'title' => 'Grocery List - Meal Planner',
            'activeNav' => 'plans',
            'planId' => $id,
            'groceryList' => $result['grocery_list'] ?? [],
        ]);
    }

    /**
     * Show prep plan
     */
    public function prep(Request $request, Response $response, array $args): Response
    {
        $id = (int) $args['id'];
        $result = $this->apiClient->post("api/plans/{$id}/prep", []);

        return $this->view->render($response, 'plans/prep.php', [
            'title' => 'Prep Plan - Meal Planner',
            'activeNav' => 'plans',
            'planId' => $id,
            'prepPlan' => $result['prep_plan'] ?? [],
        ]);
    }

    /**
     * Reroll a single recipe in the plan
     */
    public function reroll(Request $request, Response $response, array $args): Response
    {
        $planId = (int) $args['id'];
        $recipeId = (int) $args['recipeId'];

        $result = $this->apiClient->post("api/plans/{$planId}/reroll/{$recipeId}", []);

        // Check if HTMX request
        if ($request->hasHeader('HX-Request')) {
            // Return partial with new recipe row
            return $this->view->render($response, 'plans/_recipe_row.php', [
                'recipe' => $result['new_recipe'] ?? [],
                'planId' => $planId,
            ]);
        }

        return $response->withHeader('Location', "/plans/{$planId}")->withStatus(302);
    }
}
