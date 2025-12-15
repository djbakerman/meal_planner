<div class="d-flex justify-content-between align-items-center mb-4">
    <h1>Recipes</h1>
    <div class="d-flex gap-2">
        <input type="search"
               class="form-control"
               placeholder="Search recipes..."
               name="q"
               hx-get="/recipes/search"
               hx-trigger="keyup changed delay:300ms"
               hx-target="#recipe-list"
               style="width: 250px;">
    </div>
</div>

<!-- Filters -->
<div class="card mb-4">
    <div class="card-body">
        <form method="get" class="row g-3">
            <div class="col-md-3">
                <label class="form-label">Meal Type</label>
                <select name="meal_type" class="form-select" onchange="this.form.submit()">
                    <option value="">All Types</option>
                    <option value="breakfast" <?= ($filters['meal_type'] ?? '') === 'breakfast' ? 'selected' : '' ?>>Breakfast</option>
                    <option value="lunch" <?= ($filters['meal_type'] ?? '') === 'lunch' ? 'selected' : '' ?>>Lunch</option>
                    <option value="dinner" <?= ($filters['meal_type'] ?? '') === 'dinner' ? 'selected' : '' ?>>Dinner</option>
                    <option value="dessert" <?= ($filters['meal_type'] ?? '') === 'dessert' ? 'selected' : '' ?>>Dessert</option>
                    <option value="snack" <?= ($filters['meal_type'] ?? '') === 'snack' ? 'selected' : '' ?>>Snack</option>
                </select>
            </div>
            <div class="col-md-3">
                <label class="form-label">Dish Role</label>
                <select name="dish_role" class="form-select" onchange="this.form.submit()">
                    <option value="">All Roles</option>
                    <option value="main" <?= ($filters['dish_role'] ?? '') === 'main' ? 'selected' : '' ?>>Main</option>
                    <option value="side" <?= ($filters['dish_role'] ?? '') === 'side' ? 'selected' : '' ?>>Side</option>
                    <option value="sub_recipe" <?= ($filters['dish_role'] ?? '') === 'sub_recipe' ? 'selected' : '' ?>>Sub-recipe</option>
                </select>
            </div>
            <div class="col-md-3 d-flex align-items-end">
                <a href="/recipes" class="btn btn-outline-secondary">Clear Filters</a>
            </div>
        </form>
    </div>
</div>

<!-- Recipe List -->
<div id="recipe-list">
    <?php if (empty($recipes)): ?>
        <div class="alert alert-info">
            No recipes found. <a href="/catalogs">Import a catalog</a> to get started.
        </div>
    <?php else: ?>
        <div class="table-responsive">
            <table class="table table-hover">
                <thead>
                    <tr>
                        <th>Name</th>
                        <th>Chapter</th>
                        <th>Type</th>
                        <th>Prep Time</th>
                        <th>Calories</th>
                        <th>Dietary</th>
                    </tr>
                </thead>
                <tbody>
                    <?php foreach ($recipes as $recipe): ?>
                        <tr onclick="window.location='/recipes/<?= $recipe['id'] ?>'" style="cursor: pointer;">
                            <td>
                                <strong><?= e($recipe['name']) ?></strong>
                                <?php if ($recipe['dish_role'] === 'side'): ?>
                                    <span class="badge bg-secondary ms-1">Side</span>
                                <?php endif; ?>
                            </td>
                            <td><?= e($recipe['chapter'] ?? '-') ?></td>
                            <td>
                                <span class="badge <?= mealTypeBadgeClass($recipe['meal_type'] ?? 'any') ?>">
                                    <?= formatMealType($recipe['meal_type'] ?? 'any') ?>
                                </span>
                            </td>
                            <td><?= formatTime($recipe['prep_time'] ?? null) ?></td>
                            <td><?= $recipe['calories'] ?? '-' ?></td>
                            <td>
                                <?php foreach (($recipe['dietary_info'] ?? []) as $tag): ?>
                                    <span class="badge <?= dietaryBadgeClass($tag) ?> me-1"><?= e($tag) ?></span>
                                <?php endforeach; ?>
                            </td>
                        </tr>
                    <?php endforeach; ?>
                </tbody>
            </table>
        </div>

        <!-- Pagination -->
        <?php if (!empty($pagination)): ?>
            <nav>
                <ul class="pagination justify-content-center">
                    <?php if ($pagination['page'] > 1): ?>
                        <li class="page-item">
                            <a class="page-link" href="?page=<?= $pagination['page'] - 1 ?>&meal_type=<?= $filters['meal_type'] ?? '' ?>&dish_role=<?= $filters['dish_role'] ?? '' ?>">Previous</a>
                        </li>
                    <?php endif; ?>

                    <li class="page-item disabled">
                        <span class="page-link">Page <?= $pagination['page'] ?> of <?= $pagination['total_pages'] ?></span>
                    </li>

                    <?php if ($pagination['page'] < $pagination['total_pages']): ?>
                        <li class="page-item">
                            <a class="page-link" href="?page=<?= $pagination['page'] + 1 ?>&meal_type=<?= $filters['meal_type'] ?? '' ?>&dish_role=<?= $filters['dish_role'] ?? '' ?>">Next</a>
                        </li>
                    <?php endif; ?>
                </ul>
            </nav>
        <?php endif; ?>
    <?php endif; ?>
</div>
