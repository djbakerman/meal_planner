<!doctype html>
<html lang="en">

<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>
        <?= $title ?? 'Meal Planner' ?>
    </title>
    <!-- Bootstrap 5 CSS -->
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <!-- Custom CSS -->
    <link href="<?= url('/assets/css/app.css') ?>" rel="stylesheet">
    <!-- HTMX -->
    <script src="https://unpkg.com/htmx.org@1.9.4"></script>

    <!-- Social / Open Graph -->
    <meta property="og:type" content="website">
    <meta property="og:title" content="<?= h($title ?? 'Meal Planner') ?> | Dan's Meal Planner">
    <meta property="og:description"
        content="Digitize cookbooks, organize recipes, and generate automated meal plans with AI.">
    <meta property="og:image" content="<?= url('/assets/images/logo.png') ?>">
    <meta property="og:url"
        content="<?= (isset($_SERVER['HTTPS']) ? 'https://' : 'http://') . $_SERVER['HTTP_HOST'] . $_SERVER['REQUEST_URI'] ?>">
    <meta name="twitter:card" content="summary_large_image">
</head>

<body>

    <nav class="navbar navbar-expand-lg navbar-dark bg-dark">
        <div class="container">
            <a class="navbar-brand" href="<?= url('/') ?>">
                <img src="<?= url('/assets/images/logo.png') ?>" alt="Logo" width="30" height="30"
                    class="d-inline-block align-text-top me-2">
                Dan's Meal Planner
            </a>
            <button class="navbar-toggler" type="button" data-bs-toggle="collapse" data-bs-target="#navbarNav">
                <span class="navbar-toggler-icon"></span>
            </button>
            <div class="collapse navbar-collapse" id="navbarNav">
                <ul class="navbar-nav me-auto">
                    <?php $uri = $_SERVER['REQUEST_URI'] ?? '/'; ?>
                    <li class="nav-item">
                        <a class="nav-link <?= $uri === url('/') || $uri === url('') ? 'active' : '' ?>"
                            href="<?= url('/') ?>">Home</a>
                    </li>
                    <li class="nav-item">
                        <a class="nav-link <?= strpos($uri, url('/recipes')) === 0 ? 'active' : '' ?>"
                            href="<?= url('/recipes') ?>">Recipes</a>
                    </li>
                    <li class="nav-item">
                        <a class="nav-link <?= strpos($uri, url('/plans')) === 0 ? 'active' : '' ?>"
                            href="<?= url('/plans') ?>">Meal
                            Plans</a>
                    </li>
                    <?php if (isset($_SESSION['user']) && ($_SESSION['user']['role'] ?? 'user') === 'admin'): ?>
                        <li class="nav-item">
                            <a class="nav-link <?= strpos($uri, url('/catalogs')) === 0 ? 'active' : '' ?>"
                                href="<?= url('/catalogs') ?>">Catalogs</a>
                        </li>
                    <?php endif; ?>
                    <li class="nav-item">
                        <a class="nav-link <?= strpos($uri, url('/help')) === 0 ? 'active' : '' ?>"
                            href="<?= url('/help') ?>">Help</a>
                    </li>
                </ul>
                <ul class="navbar-nav">
                    <?php if (isset($_SESSION['user'])): ?>
                        <li class="nav-item">
                            <span class="nav-link text-light">Welcome, <?= h($_SESSION['user']['username']) ?></span>
                        </li>
                        <li class="nav-item">
                            <a class="nav-link btn btn-outline-danger btn-sm text-light ms-2"
                                href="<?= url('/logout') ?>">Logout</a>
                        </li>
                    <?php else: ?>
                        <li class="nav-item">
                            <a class="nav-link" href="<?= url('/login') ?>">Login</a>
                        </li>
                        <li class="nav-item">
                            <a class="nav-link" href="<?= url('/register') ?>">Register</a>
                        </li>
                    <?php endif; ?>
                </ul>
            </div>
        </div>
    </nav>

    <div class="container" id="main-content">
        <?php
        $flashes = $_SESSION['flash'] ?? [];
        unset($_SESSION['flash']);
        foreach ($flashes as $type => $messages):
            $alertType = ($type === 'error') ? 'danger' : $type;
            foreach ($messages as $msg):
                ?>
                <div class="alert alert-<?= $alertType ?> alert-dismissible fade show mt-3" role="alert">
                    <?= h($msg) ?>
                    <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
                </div>
            <?php endforeach; endforeach; ?>

        <?= $content ?>
    </div>

    <footer class="footer mt-auto py-3 bg-light text-center">
        <div class="container">
            <span class="text-muted">&copy; <?= date('Y') ?> Meal Planner. <a href="https://fiberdan.com/privacy-page/"
                    target="_blank" class="text-decoration-none text-muted">Privacy Policy</a></span>
        </div>
    </footer>

    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
    <script src="<?= url('/assets/js/app.js') ?>"></script>
</body>

</html>