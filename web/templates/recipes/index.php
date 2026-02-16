<?php
// Create a lookup map for catalog names
$catalogMap = [];
if (!empty($catalogs)) {
    foreach ($catalogs as $c) {
        $catalogMap[$c['id']] = $c['name'];
    }
}
?>
<div class="row mb-4">
    <div class="col-md-6">
        <h1>🍳 Recipes</h1>
        <p class="text-muted">Browse <?= $totalRecipes ?> recipes from your collection.</p>
    </div>
    <div class="col-md-6">
        <form action="<?= url('/recipes') ?>" method="GET" class="card card-body bg-light py-3">
            <div class="row g-2">
                <div class="col-md-12">
                    <div class="input-group">
                        <input type="text" name="search" class="form-control" placeholder="Search recipes..."
                            value="<?= h($filters['search'] ?? '') ?>">
                        <button class="btn btn-primary" type="submit">Search</button>
                    </div>
                </div>
                <div class="col-md-4">
                    <select name="meal_type" class="form-select" onchange="this.form.submit()">
                        <option value="all">Meal Type</option>
                        <?php
                        $types = ['breakfast', 'lunch', 'dinner', 'dessert', 'snack', 'any'];
                        foreach ($types as $t):
                            $selected = ($filters['meal_type'] ?? '') === $t ? 'selected' : '';
                            ?>
                            <option value="<?= $t ?>" <?= $selected ?>><?= ucfirst($t) ?></option>
                        <?php endforeach; ?>
                    </select>
                </div>
                <div class="col-md-4">
                    <select name="dish_role" class="form-select" onchange="this.form.submit()">
                        <option value="all">Dish Role</option>
                        <option value="main" <?= ($filters['dish_role'] ?? '') === 'main' ? 'selected' : '' ?>>Main Dish
                        </option>
                        <option value="side" <?= ($filters['dish_role'] ?? '') === 'side' ? 'selected' : '' ?>>Side Dish
                        </option>
                        <option value="sub_recipe" <?= ($filters['dish_role'] ?? '') === 'sub_recipe' ? 'selected' : '' ?>>
                            Sub Recipe</option>
                    </select>
                </div>
                <div class="col-md-4">
                    <select name="catalog_id" class="form-select" onchange="this.form.submit()">
                        <option value="">All Catalogs</option>
                        <?php if (!empty($catalogs)): ?>
                            <?php foreach ($catalogs as $cat):
                                $catId = (string) $cat['id'];
                                $currentCat = $filters['catalog_id'] ?? '';
                                $selected = $currentCat === $catId ? 'selected' : '';
                                ?>
                                <option value="<?= $cat['id'] ?>" <?= $selected ?>><?= h($cat['name']) ?></option>
                            <?php endforeach; ?>
                        <?php endif; ?>
                    </select>
                </div>
            </div>
        </form>
    </div>
</div>

<div class="table-responsive">
    <table class="table table-hover align-middle">
        <thead class="table-light">
            <tr>
                <th width="35%">Name</th>
                <th>Catalog</th>
                <th>Meal Type</th>
                <th>Role</th>
                <th>Chapter</th>
                <th>Action</th>
            </tr>
        </thead>
        <tbody>
            <?php if (empty($recipes)): ?>
                <tr>
                    <td colspan="5" class="text-center py-5">
                        <p class="lead text-muted">No recipes found matching your criteria.</p>
                    </td>
                </tr>
            <?php else: ?>
                <?php foreach ($recipes as $recipe): ?>
                    <tr>
                        <td>
                            <div class="fw-bold">
                                <a href="<?= url('/recipes/' . $recipe['id']) ?>" class="text-decoration-none text-dark">
                                    <?= h($recipe['name']) ?>
                                </a>
                                </a>
                            </div>
                            <?php if (!empty($recipe['description'])): ?>
                                <small class="text-muted"><?= substr(h($recipe['description']), 0, 80) ?>...</small>
                            <?php endif; ?>
                            <?php if (!empty($recipe['sub_recipes'])): ?>
                                <div class="mt-1">
                                    <span class="badge bg-light text-dark border" title="Includes sub-recipes">
                                        +<?= count($recipe['sub_recipes']) ?> components
                                    </span>
                                </div>
                            <?php endif; ?>
                        </td>
                        <td>
                            <?php if (!empty($recipe['catalog_id']) && isset($catalogMap[$recipe['catalog_id']])): ?>
                                <a href="<?= url('/recipes?catalog_id=' . $recipe['catalog_id']) ?>"
                                    class="badge bg-light text-dark text-decoration-none border">
                                    <?= h($catalogMap[$recipe['catalog_id']]) ?>
                                </a>
                            <?php elseif (!empty($recipe['catalog_id'])): ?>
                                <span class="badge bg-light text-dark border">#<?= $recipe['catalog_id'] ?></span>
                            <?php else: ?>
                                <span class="text-muted">-</span>
                            <?php endif; ?>
                        </td>
                        <td>
                            <?php
                            $badgeClass = match ($recipe['meal_type']) {
                                'dinner' => 'bg-primary',
                                'breakfast' => 'bg-warning text-dark',
                                'lunch' => 'bg-success',
                                'dessert' => 'bg-danger',
                                default => 'bg-secondary'
                            };
                            ?>
                            <span class="badge <?= $badgeClass ?>"><?= ucfirst($recipe['meal_type']) ?></span>
                        </td>
                        <td>
                            <?php
                            echo match ($recipe['dish_role']) {
                                'sub_recipe' => 'Sub-Recipe',
                                'main' => 'Main Dish',
                                'side' => 'Side Dish',
                                default => ucwords(str_replace('_', ' ', $recipe['dish_role']))
                            };
                            ?>
                        </td>
                        <td><?= h($recipe['chapter'] ?? '-') ?></td>
                        <td>
                            <div class="btn-group btn-group-sm">
                                <a href="<?= url('/recipes/' . $recipe['id']) ?>" class="btn btn-outline-primary">View</a>
                                <?php if (isset($_SESSION['user']) && ($_SESSION['user']['role'] ?? '') === 'admin'): ?>
                                    <a href="<?= url('/recipes/' . $recipe['id'] . '/edit') ?>"
                                        class="btn btn-outline-secondary">Edit</a>
                                <?php endif; ?>

                                <?php if (!empty($filters['add_to_plan'])): ?>
                                    <form action="<?= url('/plans/' . $filters['add_to_plan'] . '/add') ?>" method="POST"
                                        class="d-inline">
                                        <input type="hidden" name="recipe_id" value="<?= $recipe['id'] ?>">
                                        <button type="submit" class="btn btn-success">Add to Plan</button>
                                    </form>
                                <?php endif; ?>
                            </div>
                        </td>
                    </tr>
                <?php endforeach; ?>
            <?php endif; ?>
        </tbody>
    </table>
</div>

<!-- Pagination -->
<?php if ($totalPages > 1): ?>
    <nav aria-label="Page navigation" class="mt-4">
        <ul class="pagination justify-content-center">
            <li class="page-item <?= $currentPage <= 1 ? 'disabled' : '' ?>">
                <a class="page-link"
                    href="?<?= http_build_query(array_merge($filters, ['page' => $currentPage - 1])) ?>">Previous</a>
            </li>

            <li class="page-item disabled">
                <span class="page-link">Page <?= $currentPage ?> of <?= $totalPages ?></span>
            </li>

            <li class="page-item <?= $currentPage >= $totalPages ? 'disabled' : '' ?>">
                <a class="page-link"
                    href="?<?= http_build_query(array_merge($filters, ['page' => $currentPage + 1])) ?>">Next</a>
            </li>
        </ul>
    </nav>
<?php endif; ?>