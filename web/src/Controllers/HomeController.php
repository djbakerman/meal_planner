<?php

declare(strict_types=1);

namespace MealPlanner\Controllers;

use MealPlanner\Services\ApiClient;
use Psr\Http\Message\ResponseInterface as Response;
use Psr\Http\Message\ServerRequestInterface as Request;
use Slim\Views\PhpRenderer;

class HomeController
{
    public function __construct(
        private PhpRenderer $view,
        private ApiClient $apiClient
    ) {}

    public function index(Request $request, Response $response): Response
    {
        // Fetch dashboard stats from API
        $stats = $this->apiClient->get('stats');

        // Check API connectivity
        $apiStatus = $this->apiClient->healthCheck();

        return $this->view->render($response, 'home/index.php', [
            'title' => 'Dashboard - Meal Planner',
            'activeNav' => 'home',
            'stats' => $stats,
            'apiStatus' => $apiStatus,
        ]);
    }
}
