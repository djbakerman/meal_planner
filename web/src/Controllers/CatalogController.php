<?php

declare(strict_types=1);

namespace MealPlanner\Controllers;

use MealPlanner\Services\ApiClient;
use MealPlanner\Services\SessionService;
use Psr\Http\Message\ResponseInterface as Response;
use Psr\Http\Message\ServerRequestInterface as Request;
use Slim\Views\PhpRenderer;

class CatalogController
{
    public function __construct(
        private PhpRenderer $view,
        private ApiClient $apiClient,
        private SessionService $session
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
            'flash' => $this->session->getFlash(),
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
            $this->session->flash('error', 'Please provide a file path.');
            return $response->withHeader('Location', '/catalogs')->withStatus(302);
        }

        $result = $this->apiClient->post('api/catalogs/import', [
            'file_path' => $filePath,
        ]);

        if (isset($result['error'])) {
            $this->session->flash('error', 'Import failed: ' . $result['error']);
        } elseif (isset($result['success']) && $result['success']) {
            $msg = sprintf(
                'Successfully imported "%s": %d recipes, %d chapters',
                $result['catalog_name'] ?? 'catalog',
                $result['recipes_imported'] ?? 0,
                $result['chapters_imported'] ?? 0
            );
            $this->session->flash('success', $msg);

            if (!empty($result['errors'])) {
                $this->session->flash('warning', 'Some items had issues: ' . count($result['errors']) . ' errors');
            }
        } else {
            $this->session->flash('warning', 'Import completed with unknown status.');
        }

        return $response->withHeader('Location', '/catalogs')->withStatus(302);
    }
}
