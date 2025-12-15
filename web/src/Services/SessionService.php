<?php

declare(strict_types=1);

namespace MealPlanner\Services;

/**
 * Simple session-based flash message service
 */
class SessionService
{
    public function __construct()
    {
        if (session_status() === PHP_SESSION_NONE) {
            session_start();
        }
    }

    /**
     * Set a flash message
     */
    public function flash(string $type, string $message): void
    {
        if (!isset($_SESSION['flash'])) {
            $_SESSION['flash'] = [];
        }
        if (!isset($_SESSION['flash'][$type])) {
            $_SESSION['flash'][$type] = [];
        }
        $_SESSION['flash'][$type][] = $message;
    }

    /**
     * Get and clear all flash messages
     */
    public function getFlash(): array
    {
        $flash = $_SESSION['flash'] ?? [];
        $_SESSION['flash'] = [];
        return $flash;
    }

    /**
     * Set a session value
     */
    public function set(string $key, mixed $value): void
    {
        $_SESSION[$key] = $value;
    }

    /**
     * Get a session value
     */
    public function get(string $key, mixed $default = null): mixed
    {
        return $_SESSION[$key] ?? $default;
    }

    /**
     * Remove a session value
     */
    public function remove(string $key): void
    {
        unset($_SESSION[$key]);
    }

    /**
     * Destroy the session
     */
    public function destroy(): void
    {
        session_destroy();
        $_SESSION = [];
    }
}
