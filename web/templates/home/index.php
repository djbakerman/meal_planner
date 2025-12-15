<h1 class="mb-4">Dashboard</h1>

<!-- API Status -->
<div class="alert <?= $apiStatus ? 'alert-success' : 'alert-warning' ?> mb-4">
    <strong>API Status:</strong>
    <?= $apiStatus ? 'Connected to FastAPI backend' : 'Unable to connect to FastAPI backend (localhost:8000)' ?>
</div>

<!-- Stats Cards -->
<div class="row mb-4">
    <div class="col-md-3">
        <div class="card text-center">
            <div class="card-body">
                <h3 class="card-title"><?= $stats['recipe_count'] ?? 0 ?></h3>
                <p class="card-text text-muted">Recipes</p>
            </div>
        </div>
    </div>
    <div class="col-md-3">
        <div class="card text-center">
            <div class="card-body">
                <h3 class="card-title"><?= $stats['catalog_count'] ?? 0 ?></h3>
                <p class="card-text text-muted">Catalogs</p>
            </div>
        </div>
    </div>
    <div class="col-md-3">
        <div class="card text-center">
            <div class="card-body">
                <h3 class="card-title"><?= $stats['plan_count'] ?? 0 ?></h3>
                <p class="card-text text-muted">Meal Plans</p>
            </div>
        </div>
    </div>
    <div class="col-md-3">
        <div class="card text-center">
            <div class="card-body">
                <h3 class="card-title"><?= $stats['user_count'] ?? 0 ?></h3>
                <p class="card-text text-muted">Users</p>
            </div>
        </div>
    </div>
</div>

<!-- Quick Actions -->
<div class="card mb-4">
    <div class="card-header">
        <h5 class="mb-0">Quick Actions</h5>
    </div>
    <div class="card-body">
        <div class="d-flex gap-3 flex-wrap">
            <a href="/plans/new" class="btn btn-primary">Generate Meal Plan</a>
            <a href="/recipes" class="btn btn-outline-primary">Browse Recipes</a>
            <a href="/catalogs" class="btn btn-outline-secondary">Manage Catalogs</a>
        </div>
    </div>
</div>

<!-- Recent Meal Plans -->
<div class="card">
    <div class="card-header d-flex justify-content-between align-items-center">
        <h5 class="mb-0">Recent Meal Plans</h5>
        <a href="/plans" class="btn btn-sm btn-outline-primary">View All</a>
    </div>
    <div class="card-body">
        <?php if (!empty($stats['recent_plans'])): ?>
            <div class="table-responsive">
                <table class="table table-hover mb-0">
                    <thead>
                        <tr>
                            <th>Name</th>
                            <th>Recipes</th>
                            <th>Created</th>
                            <th></th>
                        </tr>
                    </thead>
                    <tbody>
                        <?php foreach ($stats['recent_plans'] as $plan): ?>
                            <tr>
                                <td><?= e($plan['name'] ?? 'Unnamed Plan') ?></td>
                                <td><?= $plan['recipe_count'] ?? 0 ?> recipes</td>
                                <td><?= date('M j, Y', strtotime($plan['created_at'])) ?></td>
                                <td>
                                    <a href="/plans/<?= $plan['id'] ?>" class="btn btn-sm btn-outline-primary">View</a>
                                </td>
                            </tr>
                        <?php endforeach; ?>
                    </tbody>
                </table>
            </div>
        <?php else: ?>
            <p class="text-muted mb-0">No meal plans yet. <a href="/plans/new">Generate your first plan</a>.</p>
        <?php endif; ?>
    </div>
</div>
