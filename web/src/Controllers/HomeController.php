<?php

namespace App\Controllers;

use Psr\Http\Message\ResponseInterface as Response;
use Psr\Http\Message\ServerRequestInterface as Request;
use Slim\Views\PhpRenderer;

class HomeController
{
    protected $view;

    public function __construct(PhpRenderer $view)
    {
        $this->view = $view;
    }

    public function index(Request $request, Response $response, $args): Response
    {
        // Render index view into layout
        $this->view->setLayout('layouts/main.php');
        return $this->view->render($response, 'home/index.php', [
            'title' => "Dan's Meal Planner",
            'appName' => "Dan's Meal Planner"
        ]);
    }

    public function health(Request $request, Response $response): Response
    {
        $payload = json_encode(['status' => 'ok', 'service' => 'web-frontend']);
        $response->getBody()->write($payload);
        return $response
            ->withHeader('Content-Type', 'application/json');
    }
}
