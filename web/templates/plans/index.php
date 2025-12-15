<div class="d-flex justify-content-between align-items-center mb-4">
    <h1>Meal Plans</h1>
    <a href="/plans/new" class="btn btn-primary">New Plan</a>
</div>

<?php if (empty($plans)): ?>
    <div class="alert alert-info">
        No meal plans yet. <a href="/plans/new">Generate your first meal plan</a>.
    </div>
<?php else: ?>
    <div class="table-responsive">
        <table class="table table-hover">
            <thead>
                <tr>
                    <th>Name</th>
                    <th>Recipes</th>
                    <th>Meal Types</th>
                    <th>Created</th>
                    <th>Actions</th>
                </tr>
            </thead>
            <tbody>
                <?php foreach ($plans as $plan): ?>
                    <tr>
                        <td>
                            <a href="/plans/<?= $plan['id'] ?>">
                                <strong><?= e($plan['name'] ?? 'Unnamed Plan') ?></strong>
                            </a>
                        </td>
                        <td><?= $plan['recipe_count'] ?? 0 ?> recipes</td>
                        <td>
                            <?php foreach (($plan['meal_types'] ?? []) as $type): ?>
                                <span class="badge <?= mealTypeBadgeClass($type) ?> me-1">
                                    <?= formatMealType($type) ?>
                                </span>
                            <?php endforeach; ?>
                        </td>
                        <td><?= date('M j, Y g:ia', strtotime($plan['created_at'])) ?></td>
                        <td>
                            <div class="btn-group btn-group-sm">
                                <a href="/plans/<?= $plan['id'] ?>" class="btn btn-outline-primary">View</a>
                                <a href="/plans/<?= $plan['id'] ?>/grocery" class="btn btn-outline-secondary">Grocery</a>
                                <button type="button"
                                        class="btn btn-outline-danger"
                                        hx-delete="/plans/<?= $plan['id'] ?>"
                                        hx-confirm="Delete this meal plan?"
                                        hx-target="closest tr"
                                        hx-swap="outerHTML">
                                    Delete
                                </button>
                            </div>
                        </td>
                    </tr>
                <?php endforeach; ?>
            </tbody>
        </table>
    </div>
<?php endif; ?>
