<?php

declare(strict_types=1);

return [
    'app' => [
        'name' => 'Meal Planner',
        'debug' => (bool) ($_ENV['APP_DEBUG'] ?? true),
        'url' => $_ENV['APP_URL'] ?? 'http://localhost:8080',
    ],

    'view' => [
        'template_path' => __DIR__ . '/../templates',
    ],

    'api' => [
        'base_url' => $_ENV['API_URL'] ?? 'http://localhost:8000',
        'timeout' => 30,
    ],

    'database' => [
        'host' => $_ENV['DB_HOST'] ?? 'localhost',
        'port' => $_ENV['DB_PORT'] ?? '3306',
        'database' => $_ENV['DB_DATABASE'] ?? 'meal_planner',
        'username' => $_ENV['DB_USERNAME'] ?? 'meal_user',
        'password' => $_ENV['DB_PASSWORD'] ?? '1luvMySQL!',
    ],

    'session' => [
        'name' => 'meal_planner_session',
        'lifetime' => 7200, // 2 hours
        'secure' => false,  // Set true in production with HTTPS
        'httponly' => true,
    ],
];
