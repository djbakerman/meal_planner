<nav aria-label="breadcrumb" class="mb-4">
    <ol class="breadcrumb">
        <li class="breadcrumb-item"><a href="/recipes">Recipes</a></li>
        <li class="breadcrumb-item active"><?= e($recipe['name'] ?? 'Recipe') ?></li>
    </ol>
</nav>

<div class="row">
    <!-- Main Content -->
    <div class="col-lg-8">
        <h1 class="mb-3"><?= e($recipe['name'] ?? 'Untitled Recipe') ?></h1>

        <!-- Badges -->
        <div class="mb-3">
            <span class="badge <?= mealTypeBadgeClass($recipe['meal_type'] ?? 'any') ?> me-1">
                <?= formatMealType($recipe['meal_type'] ?? 'any') ?>
            </span>
            <?php if (($recipe['dish_role'] ?? 'main') !== 'main'): ?>
                <span class="badge bg-secondary me-1"><?= ucfirst($recipe['dish_role']) ?></span>
            <?php endif; ?>
            <?php foreach (($recipe['dietary_info'] ?? []) as $tag): ?>
                <span class="badge <?= dietaryBadgeClass($tag) ?> me-1"><?= e($tag) ?></span>
            <?php endforeach; ?>
        </div>

        <!-- Description -->
        <?php if (!empty($recipe['description'])): ?>
            <p class="lead"><?= e($recipe['description']) ?></p>
        <?php endif; ?>

        <!-- Instructions -->
        <div class="card mb-4">
            <div class="card-header">
                <h5 class="mb-0">Instructions</h5>
            </div>
            <div class="card-body">
                <?php if (!empty($recipe['instructions'])): ?>
                    <ol class="mb-0">
                        <?php foreach ($recipe['instructions'] as $step): ?>
                            <li class="mb-2"><?= e($step) ?></li>
                        <?php endforeach; ?>
                    </ol>
                <?php else: ?>
                    <p class="text-muted mb-0">No instructions available.</p>
                <?php endif; ?>
            </div>
        </div>

        <!-- Tips -->
        <?php if (!empty($recipe['tips'])): ?>
            <div class="card mb-4">
                <div class="card-header">
                    <h5 class="mb-0">Tips & Variations</h5>
                </div>
                <div class="card-body">
                    <ul class="mb-0">
                        <?php foreach ($recipe['tips'] as $tip): ?>
                            <li><?= e($tip) ?></li>
                        <?php endforeach; ?>
                    </ul>
                </div>
            </div>
        <?php endif; ?>
    </div>

    <!-- Sidebar -->
    <div class="col-lg-4">
        <!-- Quick Info -->
        <div class="card mb-4">
            <div class="card-header">
                <h5 class="mb-0">Quick Info</h5>
            </div>
            <ul class="list-group list-group-flush">
                <li class="list-group-item d-flex justify-content-between">
                    <span>Serves</span>
                    <strong><?= e($recipe['serves'] ?? '-') ?></strong>
                </li>
                <li class="list-group-item d-flex justify-content-between">
                    <span>Prep Time</span>
                    <strong><?= formatTime($recipe['prep_time'] ?? null) ?></strong>
                </li>
                <li class="list-group-item d-flex justify-content-between">
                    <span>Cook Time</span>
                    <strong><?= formatTime($recipe['cook_time'] ?? null) ?></strong>
                </li>
                <li class="list-group-item d-flex justify-content-between">
                    <span>Total Time</span>
                    <strong><?= formatTime($recipe['total_time'] ?? null) ?></strong>
                </li>
                <?php if (!empty($recipe['chapter'])): ?>
                    <li class="list-group-item d-flex justify-content-between">
                        <span>Chapter</span>
                        <strong><?= e($recipe['chapter']) ?></strong>
                    </li>
                <?php endif; ?>
            </ul>
        </div>

        <!-- Nutrition -->
        <?php if (!empty($recipe['calories']) || !empty($recipe['protein'])): ?>
            <div class="card mb-4">
                <div class="card-header">
                    <h5 class="mb-0">Nutrition</h5>
                </div>
                <ul class="list-group list-group-flush">
                    <?php if (!empty($recipe['calories'])): ?>
                        <li class="list-group-item d-flex justify-content-between">
                            <span>Calories</span>
                            <strong><?= e($recipe['calories']) ?></strong>
                        </li>
                    <?php endif; ?>
                    <?php if (!empty($recipe['protein'])): ?>
                        <li class="list-group-item d-flex justify-content-between">
                            <span>Protein</span>
                            <strong><?= e($recipe['protein']) ?></strong>
                        </li>
                    <?php endif; ?>
                    <?php if (!empty($recipe['carbs'])): ?>
                        <li class="list-group-item d-flex justify-content-between">
                            <span>Carbs</span>
                            <strong><?= e($recipe['carbs']) ?></strong>
                        </li>
                    <?php endif; ?>
                    <?php if (!empty($recipe['fat'])): ?>
                        <li class="list-group-item d-flex justify-content-between">
                            <span>Fat</span>
                            <strong><?= e($recipe['fat']) ?></strong>
                        </li>
                    <?php endif; ?>
                </ul>
            </div>
        <?php endif; ?>

        <!-- Ingredients -->
        <div class="card mb-4">
            <div class="card-header">
                <h5 class="mb-0">Ingredients</h5>
            </div>
            <div class="card-body">
                <?php if (!empty($recipe['ingredients'])): ?>
                    <ul class="list-unstyled mb-0">
                        <?php foreach ($recipe['ingredients'] as $ingredient): ?>
                            <li class="mb-1">
                                <input type="checkbox" class="form-check-input me-2">
                                <?= e(is_array($ingredient) ? $ingredient['ingredient_text'] : $ingredient) ?>
                            </li>
                        <?php endforeach; ?>
                    </ul>
                <?php else: ?>
                    <p class="text-muted mb-0">No ingredients listed.</p>
                <?php endif; ?>
            </div>
        </div>

        <!-- Sub-recipes -->
        <?php if (!empty($recipe['sub_recipes'])): ?>
            <?php foreach ($recipe['sub_recipes'] as $subRecipe): ?>
                <div class="card mb-4">
                    <div class="card-header">
                        <h6 class="mb-0"><?= e($subRecipe['name'] ?? 'Sub-recipe') ?></h6>
                    </div>
                    <div class="card-body">
                        <ul class="list-unstyled mb-0">
                            <?php foreach (($subRecipe['ingredients'] ?? []) as $ingredient): ?>
                                <li class="mb-1"><?= e($ingredient) ?></li>
                            <?php endforeach; ?>
                        </ul>
                    </div>
                </div>
            <?php endforeach; ?>
        <?php endif; ?>
    </div>
</div>
