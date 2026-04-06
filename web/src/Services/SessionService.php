<?php

declare(strict_types=1);

namespace App\Services;

/**
 * Simple session-based flash message service
 */
class SessionService
{
    public function __construct()
    {
        if (session_status() === PHP_SESSION_NONE) {
            // Hardened Session Security with 30-day persistence
            $lifetime = 30 * 24 * 60 * 60;
            
            // Set custom session save path to prevent Debian/Ubuntu system cron from cleaning them up
            $sessionPath = __DIR__ . '/../../sessions';
            if (!is_dir($sessionPath)) {
                mkdir($sessionPath, 0777, true);
            }
            session_save_path($sessionPath);

            ini_set('session.gc_maxlifetime', (string) $lifetime);

            // Detect if the connection is secure (important when behind Cloudflare proxy)
            $isSecure = (isset($_SERVER['HTTPS']) && $_SERVER['HTTPS'] !== 'off') ||
                        (isset($_SERVER['HTTP_X_FORWARDED_PROTO']) && $_SERVER['HTTP_X_FORWARDED_PROTO'] === 'https');

            session_start([
                'cookie_lifetime' => $lifetime,
                'cookie_httponly' => true,
                'cookie_secure' => $isSecure,
                'cookie_samesite' => 'Lax',
                'use_strict_mode' => true,
            ]);
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
