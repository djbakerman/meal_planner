<?php

use DI\Container;
use Slim\Factory\AppFactory;
use Slim\Views\PhpRenderer;

if (session_status() === PHP_SESSION_NONE) {
    session_start();
}

// Manual .env loader (since composer/vlucas/phpdotenv unavailable in this env)
$envPath = __DIR__ . '/../../.env';
if (file_exists($envPath)) {
    $lines = file($envPath, FILE_IGNORE_NEW_LINES | FILE_SKIP_EMPTY_LINES);
    foreach ($lines as $line) {
        $line = trim($line);
        if (empty($line) || strpos($line, '#') === 0)
            continue;

        $parts = explode('=', $line, 2);
        if (count($parts) === 2) {
            $name = trim($parts[0]);
            $value = trim($parts[1]);

            // Remove quotes if present
            if (preg_match('/^"(.*)"$/', $value, $matches)) {
                $value = $matches[1];
            } elseif (preg_match("/^'(.*)'$/", $value, $matches)) {
                $value = $matches[1];
            }

            if (!array_key_exists($name, $_SERVER) && !array_key_exists($name, $_ENV)) {
                putenv(sprintf('%s=%s', $name, $value));
                $_ENV[$name] = $value;
                $_SERVER[$name] = $value;
            }
        }
    }
}

require __DIR__ . '/../vendor/autoload.php';

// Create Container using PHP-DI
$container = new Container();

// Set View Renderer
$container->set(PhpRenderer::class, function ($c) {
    return new PhpRenderer(__DIR__ . '/../templates/');
});

// Set AppFactory to use the container
AppFactory::setContainer($container);
$app = AppFactory::create();

// Support subdirectory deployment
if ($basePath = getenv('APP_BASE_PATH')) {
    $app->setBasePath($basePath);
}

// Load Routes
$routes = require __DIR__ . '/../config/routes.php';
$routes($app);

// Add Error Middleware
$app->addErrorMiddleware(true, true, true);

$app->run();
