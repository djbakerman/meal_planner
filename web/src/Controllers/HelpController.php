<?php

namespace App\Controllers;

use Psr\Http\Message\ResponseInterface as Response;
use Psr\Http\Message\ServerRequestInterface as Request;
use Slim\Views\PhpRenderer;

class HelpController
{
    protected $view;

    public function __construct(PhpRenderer $view)
    {
        $this->view = $view;
    }

    public function index(Request $request, Response $response, $args): Response
    {
        $this->view->setLayout('layouts/main.php');
        return $this->view->render($response, 'help/index.php', [
            'title' => 'Help & Documentation'
        ]);
    }
}
