<?php

namespace App\Controllers;

use Psr\Http\Message\ResponseInterface as Response;
use Psr\Http\Message\ServerRequestInterface as Request;
use Slim\Views\PhpRenderer;
use App\Services\ApiClient;

use App\Services\SessionService;

class PlanController
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
        $scope = $queryParams['scope'] ?? 'my'; // default to 'my'

        $query = ['scope' => $scope];
        $user = $request->getAttribute('user');

        // If 'my' scope, we need user_id (or api assumes user_id if needed, but safer to pass)
        // If 'community', user_id optional but good for context if API uses it later
        if ($user) {
            $query['user_id'] = $user['id'];
        }

        $plans = $this->api->get('/api/plans', $query);

        $this->view->setLayout('layouts/main.php');
        return $this->view->render($response, 'plans/index.php', [
            'title' => ($scope === 'community' ? 'Community Meal Plans' : 'My Meal Plans'),
            'plans' => $plans,
            'scope' => $scope
        ]);
    }

    // ... existing Create/Store methods ...

    public function update(Request $request, Response $response, $args): Response
    {
        $id = $args['id'];
        $user = $request->getAttribute('user');

        if (!$user) {
            $this->session->flash('error', 'Must be logged in.');
            return $response->withHeader('Location', url("/plans/{$id}"))->withStatus(302);
        }

        $data = $request->getParsedBody();
        $payload = ['user_id' => $user['id']];

        $hasUpdate = false;

        if (!empty($data['name'])) {
            $payload['name'] = $data['name'];
            $hasUpdate = true;
        }

        if (isset($data['target_servings'])) {
            $payload['target_servings'] = (int) $data['target_servings'];
            $hasUpdate = true;
        }

        if (!$hasUpdate) {
            $this->session->flash('error', 'Nothing to update.');
            return $response->withHeader('Location', url("/plans/{$id}"))->withStatus(302);
        }

        $result = $this->api->patch("/api/plans/{$id}", $payload);

        if (isset($result['detail'])) {
            $this->session->flash('error', 'Error: ' . $result['detail']);
        } else {
            $this->session->flash('success', 'Plan updated.');
        }

        return $response->withHeader('Location', url("/plans/{$id}"))->withStatus(302);
    }

    public function toggleShare(Request $request, Response $response, $args): Response
    {
        $id = $args['id'];
        $data = $request->getParsedBody();
        $user = $request->getAttribute('user');

        if (!$user) {
            $this->session->flash('error', 'Must be logged in.');
            return $response->withHeader('Location', url("/plans/{$id}"))->withStatus(302);
        }

        $isPublic = (bool) ($data['is_public'] ?? false);
        $newName = $data['new_name'] ?? null;

        $payload = [
            'user_id' => $user['id'],
            'is_public' => $isPublic
        ];

        if ($newName) {
            $payload['new_name'] = $newName;
        }

        $result = $this->api->post("/api/plans/{$id}/share", $payload);

        if (isset($result['detail'])) {
            // Check for specific conflict status code handling if ApiClient exposes status
            // Assuming ApiClient might return the error body. 
            // If the message contains specific text from API:
            $this->session->flash('error', $result['detail']);
        } elseif (isset($result['error'])) {
            $this->session->flash('error', 'Could not update visibility.');
        } else {
            $status = $isPublic ? 'Shared to Community.' : 'Made Private.';
            $this->session->flash('success', $status);
        }

        return $response->withHeader('Location', url("/plans/{$id}"))->withStatus(302);
    }

    public function toggleLike(Request $request, Response $response, $args): Response
    {
        $id = $args['id'];
        $user = $request->getAttribute('user');

        if (!$user) {
            // Maybe redirect to login? Or just error.
            $this->session->flash('error', 'Login to like plans.');
            return $response->withHeader('Location', url("/plans/{$id}"))->withStatus(302);
        }

        $payload = ['user_id' => $user['id']];
        $this->api->post("/api/plans/{$id}/like", $payload);

        // Referer check to redirect back to index or show page?
        // Simple: Redirect to show page if called from there, or back to index?
        // Let's assume called from Show page for now. 
        // If called from Index, we'd need a referer check.
        $referer = $request->getHeaderLine('Referer');
        if (strpos($referer, '/plans') !== false) {
            return $response->withHeader('Location', $referer)->withStatus(302);
        }

        return $response->withHeader('Location', url("/plans/{$id}"))->withStatus(302);
    }

    public function create(Request $request, Response $response, $args): Response
    {
        $catalogs = $this->api->get('/api/catalogs');

        $this->view->setLayout('layouts/main.php');
        return $this->view->render($response, 'plans/new.php', [
            'title' => 'Generate New Plan',
            'catalogs' => $catalogs
        ]);
    }

    public function store(Request $request, Response $response, $args): Response
    {
        $data = $request->getParsedBody();

        // Prepare payload for API
        // Prepare payload for API
        $payload = [
            'recipe_count' => 5, // Default legacy
            'days' => (int) ($data['recipe_count'] ?? 5), // Map slider to 'days'
            'meal_types' => []
        ];

        // Handle meal types checkboxes
        // If 'select_all' or nothing, maybe default?
        // Let's look at the form data structure we'll build
        if (!empty($data['meal_types']) && is_array($data['meal_types'])) {
            $payload['meal_types'] = array_keys($data['meal_types']);
        } else {
            // Nothing selected: implies "Any"
            $payload['meal_types'] = [];
        }

        // Optional: Catalog Filter (Support Multiple)
        if (!empty($data['catalog_ids'])) {
            // Handle both array and single value
            $ids = is_array($data['catalog_ids']) ? $data['catalog_ids'] : [$data['catalog_ids']];

            // Filter out empty/"Any" values
            $valid_ids = array_filter($ids, function ($v) {
                return !empty($v);
            });

            if (!empty($valid_ids)) {
                $payload['catalog_ids'] = array_map('intval', $valid_ids);
            }
        }

        // Optional: Exclusions
        if (!empty($data['excluded_ingredients'])) {
            $exclusions = explode(',', $data['excluded_ingredients']);
            $payload['excluded_ingredients'] = array_map('trim', $exclusions);
        }

        // Feature: Cumulative Count Mode
        if (!empty($data['use_cumulative_count'])) {
            $payload['use_cumulative_count'] = true;
        }

        // Feature: Target Servings
        if (!empty($data['target_servings'])) {
            $payload['target_servings'] = (int) $data['target_servings'];
        }

        // Add user_id if authenticated
        $user = $request->getAttribute('user');
        if ($user) {
            $payload['user_id'] = $user['id'];
        }

        $newPlan = $this->api->post('/api/plans/generate', $payload);

        if (isset($newPlan['id'])) {
            return $response->withHeader('Location', url('/plans/' . $newPlan['id']))->withStatus(302);
        }

        // Error handling
        return $response->withHeader('Location', url('/plans/new?error=failed'))->withStatus(302);
    }

    public function show(Request $request, Response $response, $args): Response
    {
        $id = $args['id'];
        $plan = $this->api->get("/api/plans/{$id}");

        if (!$plan || isset($plan['detail'])) {
            $response->getBody()->write("Plan not found");
            return $response->withStatus(404);
        }

        // Enrich plan recipes with details if needed, 
        // the API schema says plan_recipes has 'recipe' object nested.

        // Fetch catalogs for swap dropdown
        $catalogs = $this->api->get('/api/catalogs');

        $this->view->setLayout('layouts/main.php');
        return $this->view->render($response, 'plans/show.php', [
            'title' => $plan['name'],
            'plan' => $plan,
            'catalogs' => $catalogs,
            'flash' => $this->session->getFlash()
        ]);
    }

    public function delete(Request $request, Response $response, $args): Response
    {
        $id = $args['id'];
        $user = $request->getAttribute('user');

        if (!$user) {
            $this->session->flash('error', 'Authentication required.');
            return $response->withHeader('Location', url('/plans'))->withStatus(302);
        }

        // Call API to delete
        // Note: We need to ensure ApiClient has a 'delete' method or use POST if API expects it. 
        // The API endpoint is DELETE /api/plans/{id}. 
        // ApiClient.php DOES have a delete() method.

        // We pass user_id in query or body? 
        // The API delete_plan (api/routers/plans.py) checks ownership if user_id is in logic, 
        // but typically DELETE requests don't have bodies in some clients.
        // Let's check api/routers/plans.py.
        // It says: def delete_plan(plan_id: int, user_id: int = Query(...) ...

        $result = $this->api->delete("/api/plans/{$id}", ['user_id' => $user['id']]);

        // If success (or even if not found), redirect to index
        if (isset($result['detail'])) {
            $this->session->flash('error', 'Error: ' . $result['detail']);
            return $response->withHeader('Location', url("/plans/{$id}"))->withStatus(302);
        }

        $this->session->flash('success', 'Meal plan deleted.');
        return $response->withHeader('Location', url('/plans'))->withStatus(302);
    }

    private function getUserId(Request $request): ?int
    {
        $user = $request->getAttribute('user');
        return $user ? (int) $user['id'] : null;
    }

    private function verifyOwnership(Request $request, int $planId): bool
    {
        // For strict checking, we could fetch the plan here via API and check user_id.
        // But checking user_id on the API side is the critical path.
        // Here we just ensure we HAVE a user logged in.
        return $this->getUserId($request) !== null;
    }

    public function generateGrocery(Request $request, Response $response, $args): Response
    {
        $id = (int) $args['id'];
        $userId = $this->getUserId($request);

        $this->api->post("/api/plans/{$id}/grocery", ['user_id' => $userId]);
        return $response->withHeader('Location', url("/plans/{$id}"))->withStatus(302);
    }

    public function generatePrep(Request $request, Response $response, $args): Response
    {
        $id = (int) $args['id'];
        $userId = $this->getUserId($request);

        $this->api->post("/api/plans/{$id}/prep", ['user_id' => $userId]);
        return $response->withHeader('Location', url("/plans/{$id}"))->withStatus(302);
    }

    public function swap(Request $request, Response $response, $args): Response
    {
        $id = (int) $args['id'];
        $userId = $this->getUserId($request);

        if (!$userId) {
            // Basic frontend guard, though API handles it too
            $this->session->flash('error', 'Must be logged in to modify plans.');
            return $response->withHeader('Location', "/plans/{$id}")->withStatus(302);
        }

        $data = $request->getParsedBody();

        $recipeIds = $data['recipe_ids'] ?? [];
        $mode = $data['mode'] ?? 'random';
        $catalogId = $data['catalog_id'] ?? null;

        if (empty($recipeIds)) {
            $this->session->flash('error', 'Select at least one recipe to swap.');
            return $response->withHeader('Location', url("/plans/{$id}"))->withStatus(302);
        }

        // ensure recipes are integers
        $recipeIds = array_map('intval', $recipeIds);

        $payload = [
            'recipe_ids' => $recipeIds,
            'mode' => $mode,
            'user_id' => $userId
        ];

        if ($catalogId) {
            $payload['catalog_id'] = (int) $catalogId;
        }

        $result = $this->api->post("/api/plans/{$id}/swap", $payload);

        if (isset($result['detail'])) {
            // API returned error (e.g. Forbidden)
            $this->session->flash('error', 'Error: ' . $result['detail']);
        } else {
            if ($mode === 'similar') {
                $msg = 'Swapped for similar recipes.';
            } elseif ($mode === 'catalog') {
                $msg = 'Swapped from selected catalog.';
            } else {
                $msg = 'Swapped for random recipes.';
            }
            $this->session->flash('success', $msg);
        }

        return $response->withHeader('Location', url("/plans/{$id}"))->withStatus(302);
    }

    public function remove(Request $request, Response $response, $args): Response
    {
        $id = (int) $args['id'];
        $userId = $this->getUserId($request);

        $data = $request->getParsedBody();
        $recipeIds = $data['recipe_ids'] ?? [];

        if (empty($recipeIds)) {
            $this->session->flash('error', 'Select recipes to remove.');
            return $response->withHeader('Location', url("/plans/{$id}"))->withStatus(302);
        }

        $recipeIds = array_map('intval', $recipeIds);
        $result = $this->api->post("/api/plans/{$id}/remove", [
            'recipe_ids' => $recipeIds,
            'user_id' => $userId
        ]);

        if (isset($result['detail'])) {
            $this->session->flash('error', 'Error: ' . $result['detail']);
        } else {
            $this->session->flash('success', 'Recipes removed.');
        }

        return $response->withHeader('Location', url("/plans/{$id}"))->withStatus(302);
    }

    public function add(Request $request, Response $response, $args): Response
    {
        $id = (int) $args['id'];
        $userId = $this->getUserId($request);

        $data = $request->getParsedBody(); // from POST form on plan page

        $payload = ['user_id' => $userId];

        if (!empty($data['recipe_id'])) {
            // Explicit Add
            $payload['recipe_id'] = (int) $data['recipe_id'];
            $msg = 'Recipe added to plan.';
        } elseif (!empty($data['random'])) {
            // Random Add
            $payload['random'] = true;
            if (!empty($data['catalog_id'])) {
                $payload['catalog_id'] = (int) $data['catalog_id'];
                $msg = 'Random recipe from catalog added.';
            } else {
                $msg = 'Random recipe added.';
            }
        } else {
            $this->session->flash('error', 'Invalid add request.');
            return $response->withHeader('Location', url("/plans/{$id}"))->withStatus(302);
        }

        $result = $this->api->post("/api/plans/{$id}/add", $payload);

        if (isset($result['id'])) {
            $this->session->flash('success', $msg);
        } elseif (isset($result['detail'])) {
            $this->session->flash('error', 'Error: ' . $result['detail']);
        } else {
            $this->session->flash('error', 'Could not add recipe.');
        }

        return $response->withHeader('Location', url("/plans/{$id}"))->withStatus(302);
    }

    public function clone(Request $request, Response $response, $args): Response
    {
        $id = (int) $args['id'];
        $user = $request->getAttribute('user');

        if (!$user) {
            $this->session->flash('error', 'Must be logged in to clone plans.');
            return $response->withHeader('Location', url("/plans/{$id}"))->withStatus(302);
        }

        $result = $this->api->post("/api/plans/{$id}/clone", ['user_id' => $user['id']]);

        if (isset($result['id'])) {
            $this->session->flash('success', 'Plan cloned successfully! You can now edit your copy.');
            return $response->withHeader('Location', url('/plans/' . $result['id']))->withStatus(302);
        }

        if (isset($result['detail'])) {
            $this->session->flash('error', 'Error: ' . $result['detail']);
        } else {
            $this->session->flash('error', 'Could not clone plan.');
        }

        return $response->withHeader('Location', url("/plans/{$id}"))->withStatus(302);
    }
}
