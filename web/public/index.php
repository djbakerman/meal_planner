<?php

use DI\Container;
use Slim\Factory\AppFactory;
use Slim\Views\PhpRenderer;

if (session_status() === PHP_SESSION_NONE) {
    // 30 Days in seconds
    $lifetime = 30 * 24 * 60 * 60;

    // Set server-side GC max lifetime to match (prevents server deleting it)
    ini_set('session.gc_maxlifetime', (string) $lifetime);

    // Set cookie lifetime
    session_set_cookie_params([
        'lifetime' => $lifetime,
        'path' => '/',
        'domain' => '', // Current domain
        'secure' => isset($_SERVER['HTTPS']),
        'httponly' => true,
        'samesite' => 'Lax'
    ]);

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
$debug = filter_var($_ENV['APP_DEBUG'] ?? false, FILTER_VALIDATE_BOOLEAN);
$errorMiddleware = $app->addErrorMiddleware($debug, true, true);

// Custom Error Handler for 405 Method Not Allowed
// This handles cases where a session times out and a POST request (e.g. Generation) 
// is redirected/reloaded as GET, or simply fails auth checks in a way that routing catches first.
$errorMiddleware->setErrorHandler(
    Slim\Exception\HttpMethodNotAllowedException::class,
    function ($request, $exception, $displayErrorDetails) use ($app) {
        // Check if session is expired/missing
        if (session_status() === PHP_SESSION_NONE) session_start();
        $user = $_SESSION['user'] ?? null;
        
        $response = $app->getResponseFactory()->createResponse();

        if (!$user) {
             // Session expired: Redirect to login
             // We can also flash a message if we want, but simple redirect is robust
             if (isset($_SESSION)) {
                 $_SESSION['flash'] = ['type' => 'warning', 'message' => 'Session expired. Please login again.'];
             }
             return $response->withHeader('Location', url('/login'))->withStatus(302);
        }
        
        // Use custom error page for logged-in users
        $html = '<!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>405 Method Not Allowed</title>
            <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
        </head>
        <body class="bg-light d-flex align-items-center justify-content-center vh-100">
            <div class="text-center">
                <h1 class="display-1 fw-bold text-secondary">405</h1>
                <p class="fs-3"> <span class="text-danger">Opps!</span> Method Not Allowed.</p>
                <p class="lead">
                    The action you tried to perform is not allowed directly.
                </p>
                <a href="'.url('/plans').'" class="btn btn-primary">Go Home</a>
            </div>
        </body>
        </html>';
        
        $response->getBody()->write($html);
        return $response->withStatus(405);
    }
);

$app->run();
