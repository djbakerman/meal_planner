<?php

declare(strict_types=1);

use DI\Container;
use Slim\Factory\AppFactory;
use Slim\Views\PhpRenderer;

require __DIR__ . '/../vendor/autoload.php';

// Load environment variables
$dotenv = Dotenv\Dotenv::createImmutable(__DIR__ . '/..');
$dotenv->safeLoad();

// Load settings
$settings = require __DIR__ . '/../config/settings.php';

// Create Container
$container = new Container();

// Add settings to container
$container->set('settings', fn() => $settings);

// Add view renderer to container
$container->set('view', function () use ($settings) {
    $renderer = new PhpRenderer($settings['view']['template_path']);
    $renderer->setLayout('layouts/base.php');
    return $renderer;
});

// Add API client to container
$container->set(MealPlanner\Services\ApiClient::class, function () use ($settings) {
    return new MealPlanner\Services\ApiClient($settings['api']['base_url']);
});

// Create App with container
AppFactory::setContainer($container);
$app = AppFactory::create();

// Add error middleware
$app->addErrorMiddleware(
    $settings['app']['debug'],
    true,
    true
);

// Add body parsing middleware
$app->addBodyParsingMiddleware();

// Add routing middleware
$app->addRoutingMiddleware();

// Register routes
$routes = require __DIR__ . '/../config/routes.php';
$routes($app);

// Run app
$app->run();
