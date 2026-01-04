<?php

// Helper functions
if (!function_exists('h')) {
    function h($string)
    {
        return htmlspecialchars($string, ENT_QUOTES, 'UTF-8');
    }
}

if (!function_exists('url')) {
    function url($path = '')
    {
        $base = getenv('APP_BASE_PATH');
        if ($base === false) {
            $base = $_ENV['APP_BASE_PATH'] ?? $_SERVER['APP_BASE_PATH'] ?? '';
        }

        // Ensure path starts with / except if empty
        if ($path && strpos($path, '/') !== 0) {
            $path = '/' . $path;
        }
        return $base . $path;
    }
}
