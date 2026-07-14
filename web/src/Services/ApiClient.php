<?php

namespace App\Services;

use GuzzleHttp\Client;
use GuzzleHttp\Exception\RequestException;
use GuzzleHttp\Exception\GuzzleException;

class ApiClient
{
    private $client;
    private $baseUrl;

    public function __construct()
    {
        // Internal Docker/network URL for FastAPI
        // For development on localhost, we assume port 8000
        $this->baseUrl = getenv('API_URL') ?: 'http://127.0.0.1:8000';

        $this->client = new Client([
            'base_uri' => $this->baseUrl,
            'timeout' => 30.0,
            'headers' => [
                'X-Internal-Secret' => getenv('INTERNAL_API_KEY') ?? '',
                'Accept' => 'application/json'
            ]
        ]);
    }

    public function get($endpoint, $query = [])
    {
        try {
            $response = $this->client->request('GET', $endpoint, [
                'query' => $query
            ]);
            return json_decode($response->getBody(), true);
        } catch (GuzzleException $e) {
            error_log("API GET Request Error: " . $e->getMessage());
            if ($e instanceof RequestException && $e->hasResponse()) {
                error_log("API Response: " . $e->getResponse()->getBody()->getContents());
            }
            return [];
        }
    }

    public function postMultipart($endpoint, $files = [], $data = [])
    {
        try {
            $multipart = [];

            // Add files
            foreach ($files as $name => $path) {
                $multipart[] = [
                    'name' => $name,
                    'contents' => fopen($path, 'r'),
                    'filename' => basename($path)
                ];
            }

            // Add other data fields
            foreach ($data as $key => $value) {
                $multipart[] = [
                    'name' => $key,
                    'contents' => $value
                ];
            }

            $response = $this->client->request('POST', $endpoint, [
                'multipart' => $multipart
            ]);
            return json_decode($response->getBody(), true);
        } catch (RequestException $e) {
            return ['error' => $e->getMessage()];
        }
    }

    /**
     * @param float|null $timeout Per-request timeout override in seconds.
     *                            AI-backed endpoints (grocery, prep, weekly
     *                            generation) can exceed the 30s default.
     */
    public function post($endpoint, $data = [], $timeout = null)
    {
        try {
            $options = ['json' => $data];
            if ($timeout !== null) {
                $options['timeout'] = (float) $timeout;
            }
            $response = $this->client->request('POST', $endpoint, $options);
            return json_decode($response->getBody(), true);
        } catch (GuzzleException $e) {
            // GuzzleException also covers ConnectException (timeouts/resets),
            // which RequestException alone does NOT - an uncaught timeout here
            // used to surface as a Slim Application Error page.
            error_log("API POST Error: " . $e->getMessage());
            if ($e instanceof RequestException && $e->hasResponse()) {
                $body = $e->getResponse()->getBody()->getContents();
                error_log("API Body: " . $body);
                $json = json_decode($body, true);
                if ($json)
                    return $json;
            }
            return ['error' => $e->getMessage()];
        }
    }

    public function patch($endpoint, $data = [])
    {
        try {
            $response = $this->client->request('PATCH', $endpoint, [
                'json' => $data
            ]);
            return json_decode($response->getBody(), true);
        } catch (RequestException $e) {
            // Return validation errors as result to handle 422/409 gracefully
            if ($e->hasResponse()) {
                $body = $e->getResponse()->getBody()->getContents();
                $json = json_decode($body, true);
                if ($json)
                    return $json;
            }
            return ['error' => $e->getMessage()];
        }
    }

    public function put($endpoint, $data = [])
    {
        try {
            $response = $this->client->request('PUT', $endpoint, [
                'json' => $data
            ]);
            return json_decode($response->getBody(), true);
        } catch (RequestException $e) {
            return ['error' => $e->getMessage()];
        }
    }

    public function delete($endpoint, $query = [])
    {
        try {
            $response = $this->client->request('DELETE', $endpoint, [
                'query' => $query
            ]);
            return json_decode($response->getBody(), true);
        } catch (RequestException $e) {
            return ['error' => $e->getMessage()];
        }
    }
}
