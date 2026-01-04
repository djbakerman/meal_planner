<?php

declare(strict_types=1);

namespace App\Controllers;

use App\Services\ApiClient;
use App\Services\SessionService;
use Psr\Http\Message\ResponseInterface as Response;
use Psr\Http\Message\ServerRequestInterface as Request;
use Slim\Views\PhpRenderer;

class AuthController
{
    public function __construct(
        private PhpRenderer $view,
        private ApiClient $apiClient,
        private SessionService $session
    ) {
    }

    /**
     * Show login form
     */
    public function loginForm(Request $request, Response $response): Response
    {
        // Redirect if already logged in
        if ($this->session->get('user')) {
            return $response->withHeader('Location', url('/'))->withStatus(302);
        }

        $this->view->setLayout('layouts/main.php');
        return $this->view->render($response, 'auth/login.php', [
            'title' => 'Login - Meal Planner',
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
            return $response->withHeader('Location', url('/login'))->withStatus(302);
        }

        $result = $this->apiClient->post('api/auth/login', [
            'email' => $email,
            'password' => $password,
        ]);

        if (isset($result['error']) || !isset($result['success']) || !$result['success']) {
            $error = $result['detail'] ?? $result['error'] ?? 'Invalid email or password.';
            $this->session->flash('error', $error);
            return $response->withHeader('Location', url('/login'))->withStatus(302);
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
            return $response->withHeader('Location', url('/'))->withStatus(302);
        }

        $this->view->setLayout('layouts/main.php');
        return $this->view->render($response, 'auth/register.php', [
            'title' => 'Register - Meal Planner',
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
            return $response->withHeader('Location', url('/register'))->withStatus(302);
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

        return $response->withHeader('Location', url('/'))->withStatus(302);
    }

    /**
     * Logout
     */
    public function logout(Request $request, Response $response): Response
    {
        $this->session->remove('user');
        $this->session->flash('success', 'You have been logged out.');

        return $response->withHeader('Location', url('/login'))->withStatus(302);
    }
    /**
     * Google Login Start
     */
    public function googleLogin(Request $request, Response $response): Response
    {
        $clientId = $_ENV['GOOGLE_CLIENT_ID'] ?? '';
        $redirectUri = $_ENV['GOOGLE_REDIRECT_URI'] ?? 'https://fiberdan.com/meal-planner/redirect';

        // Scope for getting email and profile
        $scope = urlencode('https://www.googleapis.com/auth/userinfo.email https://www.googleapis.com/auth/userinfo.profile');

        $authUrl = "https://accounts.google.com/o/oauth2/auth?redirect_uri={$redirectUri}&response_type=code&client_id={$clientId}&scope={$scope}&access_type=offline&prompt=consent";

        return $response->withHeader('Location', $authUrl)->withStatus(302);
    }

    /**
     * Google Login Callback
     */
    public function googleCallback(Request $request, Response $response): Response
    {
        $params = $request->getQueryParams();
        $code = $params['code'] ?? null;

        if (!$code) {
            $this->session->flash('error', 'Google login failed: No code returned.');
            return $response->withHeader('Location', url('/login'))->withStatus(302);
        }

        $clientId = $_ENV['GOOGLE_CLIENT_ID'] ?? '';
        $clientSecret = $_ENV['GOOGLE_CLIENT_SECRET'] ?? '';
        $redirectUri = $_ENV['GOOGLE_REDIRECT_URI'] ?? 'https://fiberdan.com/meal-planner/redirect';

        $client = new \GuzzleHttp\Client();

        try {
            // 1. Exchange Code for Token
            $tokenResponse = $client->post('https://oauth2.googleapis.com/token', [
                'form_params' => [
                    'code' => $code,
                    'client_id' => $clientId,
                    'client_secret' => $clientSecret,
                    'redirect_uri' => $redirectUri,
                    'grant_type' => 'authorization_code'
                ]
            ]);

            $tokenData = json_decode($tokenResponse->getBody()->getContents(), true);
            $accessToken = $tokenData['access_token'];

            // 2. Get User Info
            $userResponse = $client->get('https://www.googleapis.com/oauth2/v2/userinfo', [
                'headers' => [
                    'Authorization' => "Bearer {$accessToken}"
                ]
            ]);

            $googleUser = json_decode($userResponse->getBody()->getContents(), true);

            // 3. Login/Register in API
            $result = $this->apiClient->post('api/auth/oauth-login', [
                'email' => $googleUser['email'],
                'google_id' => $googleUser['id'],
                'name' => $googleUser['name'] ?? null,
                'avatar_url' => $googleUser['picture'] ?? null
            ]);

            if (isset($result['error']) || !isset($result['success']) || !$result['success']) {
                $error = $result['error'] ?? 'Login failed.';
                $this->session->flash('error', $error);
                return $response->withHeader('Location', url('/login'))->withStatus(302);
            }

            // 4. Success
            $this->session->set('user', $result['user']);
            $this->session->flash('success', "Welcome, {$result['user']['username']}!");
            return $response->withHeader('Location', url('/'))->withStatus(302);

        } catch (\Exception $e) {
            $this->session->flash('error', 'Google login error: ' . $e->getMessage());
            return $response->withHeader('Location', url('/login'))->withStatus(302);
        }
    }
}
