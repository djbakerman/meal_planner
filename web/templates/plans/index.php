<div class="row mb-4 align-items-center">
    <div class="col-8">
        <h1>📅 Meal Plans</h1>
        <p class="text-muted">Your generated weekly menus.</p>
    </div>
    <div class="col-4 text-end">
        <a href="<?= url('/plans/new') ?>" class="btn btn-primary btn-lg shadow-sm">
            ✨ New Plan
        </a>
    </div>
</div>

<ul class="nav nav-tabs mb-4">
    <li class="nav-item">
        <a class="nav-link <?= ($scope ?? 'my') === 'my' ? 'active' : '' ?>" href="<?= url('/plans?scope=my') ?>">My
            Plans</a>
    </li>
    <li class="nav-item">
        <a class="nav-link <?= ($scope ?? 'my') === 'community' ? 'active' : '' ?>"
            href="<?= url('/plans?scope=community') ?>">Community Plans</a>
    </li>
</ul>

<div class="row">
    <?php if (empty($plans)): ?>
        <div class="col-12 text-center py-5">
            <div class="p-5 bg-light rounded-3">
                <div class="display-1 mb-3">🍽️</div>
                <h2>No plans yet</h2>
                <p class="lead">Ready to automate your week? Generate your first meal plan now.</p>
                <a href="<?= url('/plans/new') ?>" class="btn btn-primary">Start Generating</a>
            </div>
        </div>
    <?php else: ?>
        <?php foreach ($plans as $plan): ?>
            <div class="col-md-4 mb-4">
                <div class="card h-100 shadow-hover border-0 bg-white">
                    <div class="card-body">
                        <h5 class="card-title text-primary">
                            <a href="<?= url('/plans/' . $plan['id']) ?>" class="text-decoration-none stretched-link">
                                <?= h($plan['name']) ?>
                            </a>
                        </h5>
                        <p class="text-muted small mb-2">
                            <?= date('F j, Y, g:i a', strtotime($plan['created_at'])) ?>
                        </p>
                        <div class="d-flex align-items-center justify-content-between mt-3">
                            <span class="badge bg-light text-dark border">
                                <?= $plan['recipe_count'] ?> Meals
                            </span>

                            <?php if (!empty($plan['grocery_list'])): ?>
                                <span class="badge bg-success" title="Grocery List Ready">🛒 Ready</span>
                            <?php endif; ?>

                            <?php if (($plan['is_public'] ?? false)): ?>
                                <span class="badge bg-info text-dark" title="Public">🌍 Public</span>
                            <?php endif; ?>

                            <span class="badge bg-danger">❤️ <?= $plan['likes_count'] ?? 0 ?></span>
                        </div>
                    </div>
                    <div class="card-footer bg-transparent border-top-0">
                        <div class="d-flex gap-1">
                            <?php
                            // Show first 3 meal types as badges
                            $types = $plan['meal_types'] ?? [];
                            foreach (array_slice($types, 0, 3) as $type):
                                ?>
                                <span class="badge bg-secondary opacity-75" style="font-size: 0.7em"><?= ucfirst($type) ?></span>
                            <?php endforeach; ?>
                        </div>
                    </div>
                </div>
            </div>
        <?php endforeach; ?>
    <?php endif; ?>
</div>