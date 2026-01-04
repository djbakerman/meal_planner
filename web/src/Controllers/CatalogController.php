<?php

namespace App\Controllers;

use Psr\Http\Message\ResponseInterface as Response;
use Psr\Http\Message\ServerRequestInterface as Request;
use Slim\Views\PhpRenderer;
use App\Services\ApiClient;

use App\Services\SessionService;

class CatalogController
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
        // Fetch catalogs from API
        $catalogs = $this->api->get('/api/catalogs');

        $this->view->setLayout('layouts/main.php');
        return $this->view->render($response, 'catalogs/index.php', [
            'title' => 'Recipe Catalogs',
            'catalogs' => $catalogs
        ]);
    }

    public function import(Request $request, Response $response): Response
    {
        $uploadedFiles = $request->getUploadedFiles();

        // Handle file upload
        if (!empty($uploadedFiles['catalog_file'])) {
            $uploadedFile = $uploadedFiles['catalog_file'];
            if ($uploadedFile->getError() === UPLOAD_ERR_OK) {
                $filename = $uploadedFile->getClientFilename();
                $tempPath = sys_get_temp_dir() . '/' . $filename;
                $uploadedFile->moveTo($tempPath);

                // Send to API
                $result = $this->api->postMultipart('/api/catalogs/import', [
                    'file' => $tempPath
                ]);

                // Cleanup temp file
                if (file_exists($tempPath)) {
                    unlink($tempPath);
                }

                if (isset($result['message'])) {
                    $this->session->flash('success', 'Import started for ' . $filename);
                } else {
                    $error = $result['error'] ?? 'Unknown error';
                    $this->session->flash('error', 'Import failed: ' . $error);
                }
            } else {
                $this->session->flash('error', 'File upload error.');
            }
        } else {
            $this->session->flash('error', 'No file uploaded.');
        }

        return $response->withHeader('Location', url('/catalogs'))->withStatus(302);
    }

    public function show(Request $request, Response $response, $args): Response
    {
        $id = $args['id'];
        $catalog = $this->api->get("/api/catalogs/{$id}");

        if (!$catalog || isset($catalog['detail'])) {
            $this->session->flash('error', 'Catalog not found.');
            return $response->withHeader('Location', url('/catalogs'))->withStatus(302);
        }

        $this->view->setLayout('layouts/main.php');
        return $this->view->render($response, 'catalogs/show.php', [
            'title' => $catalog['name'],
            'catalog' => $catalog,
            'flash' => $this->session->getFlash()
        ]);
    }

    public function update(Request $request, Response $response, $args): Response
    {
        $id = $args['id'];
        $data = $request->getParsedBody();

        if (!empty($data['name'])) {
            $this->api->put("/api/catalogs/{$id}", ['name' => $data['name']]);
            $this->session->flash('success', 'Catalog renamed.');
        }

        return $response->withHeader('Location', url("/catalogs/{$id}"))->withStatus(302);
    }

    public function delete(Request $request, Response $response, $args): Response
    {
        $id = $args['id'];
        $this->api->delete("/api/catalogs/{$id}");
        $this->session->flash('success', 'Catalog and all its recipes deleted.');
        return $response->withHeader('Location', url('/catalogs'))->withStatus(302);
    }
}
