<div class="row">
    <div class="col-md-12 text-center">
        <img src="<?= url('/assets/images/logo.png') ?>" alt="Logo" class="img-fluid mb-4" style="max-height: 200px;">
        <h1 class="display-4">Welcome to <?= h($appName) ?></h1>
        <p class="lead">Your AI-powered assistant for digitizing cookbooks and planning meals.</p>

        <div class="row justify-content-center my-4">
            <div class="col-md-8 text-start">
                <div class="alert alert-light border">
                    <h5 class="alert-heading">About Dan's Meal Planner</h5>
                    <p class="mb-2">
                        This application helps users digitize their physical cookbooks, organize recipes into catalogs,
                        and generate automated meal plans with grocery lists. It uses AI to suggest recipes and creates
                        shopping lists to reduce food waste and simplify weekly planning.
                    </p>
                    <hr>
                    <h6 class="fw-bold">Privacy & Data Usage</h6>
                    <p class="mb-0 small text-muted">
                        We value your privacy. When you sign in with Google, we only access your basic profile
                        information
                        (Name, Email, and Profile Picture) to create your account and personalize your experience.
                        We do not share your data with third parties.
                        Your email is used solely to save your meal plans, shopping lists, and recipe catalogs securely.
                        <br>
                        <a href="https://fiberdan.com/privacy-page/" target="_blank" class="text-decoration-none">Read
                            our full Privacy Policy</a>.
                    </p>
                </div>
            </div>
        </div>

        <div class="my-4">
            <a href="<?= url('/help') ?>" class="btn btn-outline-info">📘 Learn How It Works</a>
        </div>

        <hr class="my-4">
        <p>Use the navigation above to get started.</p>

        <div class="row mt-5">
            <div class="col-md-4">
                <div class="card h-100">
                    <div class="card-body">
                        <h5 class="card-title">🍲 Browse Recipes</h5>
                        <p class="card-text">View and manage your digitized recipes from cookbooks.</p>
                        <a href="<?= url('/recipes') ?>" class="btn btn-primary">Browse Recipes</a>
                    </div>
                </div>
            </div>
            <div class="col-md-4">
                <div class="card h-100">
                    <div class="card-body">
                        <h5 class="card-title">📅 Meal Planner</h5>
                        <p class="card-text">Generate meal plans and shopping lists.</p>
                        <a href="<?= url('/plans') ?>" class="btn btn-primary">Plan Meals</a>
                    </div>
                </div>
            </div>
            <?php if (isset($_SESSION['user']) && ($_SESSION['user']['role'] ?? 'user') === 'admin'): ?>
                <div class="col-md-4">
                    <div class="card h-100">
                        <div class="card-body">
                            <h5 class="card-title">📂 Manage Catalogs</h5>
                            <p class="card-text">Import new catalogs and manage your collections.</p>
                            <a href="<?= url('/catalogs') ?>" class="btn btn-outline-secondary">Manage Catalogs</a>
                        </div>
                    </div>
                </div>
            <?php endif; ?>
        </div>
    </div>
</div>