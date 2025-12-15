<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title><?= $title ?? 'Meal Planner' ?></title>

    <!-- Bootstrap 5 CSS -->
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet" integrity="sha384-T3c6CoIi6uLrA9TneNEoa7RxnatzjcDSCmG1MXxSR1GAsXEV/Dwwykc2MPK8M2HN" crossorigin="anonymous">

    <!-- HTMX -->
    <script src="https://unpkg.com/htmx.org@1.9.10" integrity="sha384-D1Kt99CQMDuVetoL1lrYwg5t+9QdHe7NLX/SoJYkXDFfX37iInKRy5xLSi8nO7UC" crossorigin="anonymous"></script>

    <!-- Minimal custom styles -->
    <style>
        body { padding-top: 56px; }
        .htmx-indicator { display: none; }
        .htmx-request .htmx-indicator { display: inline-block; }
        .htmx-request.htmx-indicator { display: inline-block; }
        .table-hover tbody tr { cursor: pointer; }
        .badge { font-weight: 500; }
        pre { white-space: pre-wrap; word-wrap: break-word; }
    </style>
</head>
<body>
    <!-- Navigation -->
    <nav class="navbar navbar-expand-lg navbar-dark bg-dark fixed-top">
        <div class="container">
            <a class="navbar-brand" href="/">Meal Planner</a>
            <button class="navbar-toggler" type="button" data-bs-toggle="collapse" data-bs-target="#navbarNav">
                <span class="navbar-toggler-icon"></span>
            </button>
            <div class="collapse navbar-collapse" id="navbarNav">
                <ul class="navbar-nav me-auto">
                    <li class="nav-item">
                        <a class="nav-link <?= ($activeNav ?? '') === 'home' ? 'active' : '' ?>" href="/">Dashboard</a>
                    </li>
                    <li class="nav-item">
                        <a class="nav-link <?= ($activeNav ?? '') === 'recipes' ? 'active' : '' ?>" href="/recipes">Recipes</a>
                    </li>
                    <li class="nav-item">
                        <a class="nav-link <?= ($activeNav ?? '') === 'plans' ? 'active' : '' ?>" href="/plans">Meal Plans</a>
                    </li>
                    <li class="nav-item">
                        <a class="nav-link <?= ($activeNav ?? '') === 'catalogs' ? 'active' : '' ?>" href="/catalogs">Catalogs</a>
                    </li>
                </ul>
            </div>
        </div>
    </nav>

    <!-- Flash Messages -->
    <?php if (!empty($flash)): ?>
    <div class="container mt-3">
        <?php foreach ($flash as $type => $messages): ?>
            <?php foreach ((array)$messages as $message): ?>
                <div class="alert alert-<?= $type === 'error' ? 'danger' : $type ?> alert-dismissible fade show" role="alert">
                    <?= htmlspecialchars($message) ?>
                    <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
                </div>
            <?php endforeach; ?>
        <?php endforeach; ?>
    </div>
    <?php endif; ?>

    <!-- Main Content -->
    <main class="container py-4">
        <?= $content ?>
    </main>

    <!-- Footer -->
    <footer class="container py-4 mt-5 border-top">
        <p class="text-muted text-center mb-0">Meal Planner &copy; <?= date('Y') ?></p>
    </footer>

    <!-- Bootstrap 5 JS -->
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/js/bootstrap.bundle.min.js" integrity="sha384-C6RzsynM9kWDrMNeT87bh95OGNyZPhcTNXj1NW7RuBCsyN/o0jlpcV8Qyq46cDfL" crossorigin="anonymous"></script>

    <!-- HTMX configuration -->
    <script>
        document.body.addEventListener('htmx:configRequest', (event) => {
            // Add CSRF token if needed
        });

        document.body.addEventListener('htmx:afterSwap', (event) => {
            // Re-initialize tooltips after HTMX swap
            const tooltips = document.querySelectorAll('[data-bs-toggle="tooltip"]');
            tooltips.forEach(el => new bootstrap.Tooltip(el));
        });
    </script>
</body>
</html>
