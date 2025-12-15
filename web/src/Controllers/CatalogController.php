<?php

declare(strict_types=1);

namespace MealPlanner\Controllers;

use MealPlanner\Services\ApiClient;
use Psr\Http\Message\ResponseInterface as Response;
use Psr\Http\Message\ServerRequestInterface as Request;
use Slim\Views\PhpRenderer;

class CatalogController
{
    public function __construct(
        private PhpRenderer $view,
        private ApiClient $apiClient
    ) {}

    /**
     * List all catalogs
     */
    public function index(Request $request, Response $response): Response
    {
        $result = $this->apiClient->get('api/catalogs');

        return $this->view->render($response, 'catalogs/index.php', [
            'title' => 'Catalogs - Meal Planner',
            'activeNav' => 'catalogs',
            'catalogs' => $result['catalogs'] ?? [],
        ]);
    }

    /**
     * Import a JSON catalog file
     */
    public function import(Request $request, Response $response): Response
    {
        $data = $request->getParsedBody();
        $filePath = $data['file_path'] ?? '';

        if (empty($filePath)) {
            // Redirect back with error
            return $response->withHeader('Location', '/catalogs')->withStatus(302);
        }

        $result = $this->apiClient->post('api/catalogs/import', [
            'file_path' => $filePath,
        ]);

        // Redirect back to catalogs list
        return $response->withHeader('Location', '/catalogs')->withStatus(302);
    }
}
