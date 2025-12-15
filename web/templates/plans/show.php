<nav aria-label="breadcrumb" class="mb-4">
    <ol class="breadcrumb">
        <li class="breadcrumb-item"><a href="/plans">Meal Plans</a></li>
        <li class="breadcrumb-item active"><?= e($plan['name'] ?? 'Meal Plan') ?></li>
    </ol>
</nav>

<div class="d-flex justify-content-between align-items-center mb-4">
    <h1><?= e($plan['name'] ?? 'Meal Plan') ?></h1>
    <div class="btn-group">
        <a href="/plans/<?= $plan['id'] ?>/grocery" class="btn btn-outline-primary">Grocery List</a>
        <a href="/plans/<?= $plan['id'] ?>/prep" class="btn btn-outline-primary">Prep Plan</a>
    </div>
</div>

<!-- Plan Info -->
<div class="mb-4">
    <span class="text-muted">Created <?= date('M j, Y g:ia', strtotime($plan['created_at'])) ?></span>
    <?php foreach (($plan['meal_types'] ?? []) as $type): ?>
        <span class="badge <?= mealTypeBadgeClass($type) ?> ms-2"><?= formatMealType($type) ?></span>
    <?php endforeach; ?>
</div>

<!-- Recipe List -->
<div class="card">
    <div class="card-header">
        <h5 class="mb-0">Recipes (<?= count($plan['recipes'] ?? []) ?>)</h5>
    </div>
    <div class="table-responsive">
        <table class="table table-hover mb-0">
            <thead>
                <tr>
                    <th>#</th>
                    <th>Recipe</th>
                    <th>Type</th>
                    <th>Prep Time</th>
                    <th>Serves</th>
                    <th></th>
                </tr>
            </thead>
            <tbody id="recipe-list">
                <?php foreach (($plan['recipes'] ?? []) as $index => $recipe): ?>
                    <tr id="recipe-row-<?= $recipe['id'] ?>">
                        <td><?= $index + 1 ?></td>
                        <td>
                            <a href="/recipes/<?= $recipe['id'] ?>">
                                <strong><?= e($recipe['name']) ?></strong>
                            </a>
                            <?php if (!empty($recipe['chapter'])): ?>
                                <br><small class="text-muted"><?= e($recipe['chapter']) ?></small>
                            <?php endif; ?>
                        </td>
                        <td>
                            <span class="badge <?= mealTypeBadgeClass($recipe['meal_type'] ?? 'any') ?>">
                                <?= formatMealType($recipe['meal_type'] ?? 'any') ?>
                            </span>
                        </td>
                        <td><?= formatTime($recipe['prep_time'] ?? null) ?></td>
                        <td><?= e($recipe['serves'] ?? '-') ?></td>
                        <td>
                            <button type="button"
                                    class="btn btn-sm btn-outline-secondary"
                                    hx-post="/plans/<?= $plan['id'] ?>/reroll/<?= $recipe['id'] ?>"
                                    hx-target="#recipe-row-<?= $recipe['id'] ?>"
                                    hx-swap="outerHTML"
                                    title="Replace with a different recipe">
                                Reroll
                            </button>
                        </td>
                    </tr>
                <?php endforeach; ?>
            </tbody>
        </table>
    </div>
</div>

<!-- Actions -->
<div class="mt-4">
    <button type="button"
            class="btn btn-outline-danger"
            hx-delete="/plans/<?= $plan['id'] ?>"
            hx-confirm="Delete this meal plan?"
            hx-redirect="/plans">
        Delete Plan
    </button>
</div>
