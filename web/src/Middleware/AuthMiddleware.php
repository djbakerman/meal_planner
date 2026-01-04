<?php

declare(strict_types=1);

namespace App\Middleware;

use App\Services\SessionService;
use Psr\Http\Message\ResponseInterface as Response;
use Psr\Http\Message\ServerRequestInterface as Request;
use Psr\Http\Server\MiddlewareInterface;
use Psr\Http\Server\RequestHandlerInterface as RequestHandler;
use Slim\Psr7\Response as SlimResponse;

/**
 * Authentication middleware
 * Redirects unauthenticated users to login page
 */
class AuthMiddleware implements MiddlewareInterface
{
    public function __construct(
        private SessionService $session
    ) {
    }

    public function process(Request $request, RequestHandler $handler): Response
    {
        $user = $this->session->get('user');

        if (!$user) {
            // Store the intended URL for redirect after login
            $uri = $request->getUri();
            $path = $uri->getPath();

            // Don't redirect back to auth pages
            if (!in_array($path, ['/login', '/register', '/logout'])) {
                $this->session->set('redirect_after_login', $path);
            }

            $this->session->flash('warning', 'Please login to continue.');

            $response = new SlimResponse();
            return $response->withHeader('Location', url('/login'))->withStatus(302);
        }

        // Add user to request attributes for use in controllers
        $request = $request->withAttribute('user', $user);

        return $handler->handle($request);
    }
}
