<?php

declare(strict_types=1);

namespace MealPlanner\Controllers;

use MealPlanner\Services\ApiClient;
use MealPlanner\Services\SessionService;
use Psr\Http\Message\ResponseInterface as Response;
use Psr\Http\Message\ServerRequestInterface as Request;
use Slim\Views\PhpRenderer;

class AuthController
{
    public function __construct(
        private PhpRenderer $view,
        private ApiClient $apiClient,
        private SessionService $session
    ) {}

    /**
     * Show login form
     */
    public function loginForm(Request $request, Response $response): Response
    {
        // Redirect if already logged in
        if ($this->session->get('user')) {
            return $response->withHeader('Location', '/')->withStatus(302);
        }

        return $this->view->render($response, 'auth/login.php', [
            'title' => 'Login - Meal Planner',
            'flash' => $this->session->getFlash(),
        ]);
    }

    /**
     * Process login
     */
    public function login(Request $request, Response $response): Response
    {
        $data = $request->getParsedBody();
        $email = trim($data['email'] ?? '');
        $password = $data['password'] ?? '';

        if (empty($email) || empty($password)) {
            $this->session->flash('error', 'Please enter email and password.');
            return $response->withHeader('Location', '/login')->withStatus(302);
        }

        $result = $this->apiClient->post('api/auth/login', [
            'email' => $email,
            'password' => $password,
        ]);

        if (isset($result['error']) || !isset($result['success']) || !$result['success']) {
            $error = $result['detail'] ?? $result['error'] ?? 'Invalid email or password.';
            $this->session->flash('error', $error);
            return $response->withHeader('Location', '/login')->withStatus(302);
        }

        // Store user in session
        $this->session->set('user', $result['user']);
        $this->session->flash('success', 'Welcome back, ' . $result['user']['username'] . '!');

        // Redirect to intended URL or home
        $redirect = $this->session->get('redirect_after_login', '/');
        $this->session->remove('redirect_after_login');

        return $response->withHeader('Location', $redirect)->withStatus(302);
    }

    /**
     * Show registration form
     */
    public function registerForm(Request $request, Response $response): Response
    {
        // Redirect if already logged in
        if ($this->session->get('user')) {
            return $response->withHeader('Location', '/')->withStatus(302);
        }

        return $this->view->render($response, 'auth/register.php', [
            'title' => 'Register - Meal Planner',
            'flash' => $this->session->getFlash(),
        ]);
    }

    /**
     * Process registration
     */
    public function register(Request $request, Response $response): Response
    {
        $data = $request->getParsedBody();
        $username = trim($data['username'] ?? '');
        $email = trim($data['email'] ?? '');
        $password = $data['password'] ?? '';
        $confirmPassword = $data['confirm_password'] ?? '';

        // Validation
        if (empty($username) || empty($email) || empty($password)) {
            $this->session->flash('error', 'All fields are required.');
            return $response->withHeader('Location', '/register')->withStatus(302);
        }

        if (strlen($username) < 3) {
            $this->session->flash('error', 'Username must be at least 3 characters.');
            return $response->withHeader('Location', '/register')->withStatus(302);
        }

        if (!filter_var($email, FILTER_VALIDATE_EMAIL)) {
            $this->session->flash('error', 'Please enter a valid email address.');
            return $response->withHeader('Location', '/register')->withStatus(302);
        }

        if (strlen($password) < 6) {
            $this->session->flash('error', 'Password must be at least 6 characters.');
            return $response->withHeader('Location', '/register')->withStatus(302);
        }

        if ($password !== $confirmPassword) {
            $this->session->flash('error', 'Passwords do not match.');
            return $response->withHeader('Location', '/register')->withStatus(302);
        }

        $result = $this->apiClient->post('api/auth/register', [
            'username' => $username,
            'email' => $email,
            'password' => $password,
        ]);

        if (isset($result['error']) || !isset($result['success']) || !$result['success']) {
            $error = $result['detail'] ?? $result['error'] ?? 'Registration failed. Please try again.';
            $this->session->flash('error', $error);
            return $response->withHeader('Location', '/register')->withStatus(302);
        }

        // Auto-login after registration
        $this->session->set('user', $result['user']);
        $this->session->flash('success', 'Welcome to Meal Planner, ' . $result['user']['username'] . '!');

        return $response->withHeader('Location', '/')->withStatus(302);
    }

    /**
     * Logout
     */
    public function logout(Request $request, Response $response): Response
    {
        $this->session->remove('user');
        $this->session->flash('success', 'You have been logged out.');

        return $response->withHeader('Location', '/login')->withStatus(302);
    }
}
