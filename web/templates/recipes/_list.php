<?php
/**
 * Recipe list partial - used for HTMX search responses
 */
?>
<?php if (empty($recipes)): ?>
    <div class="alert alert-info">
        No recipes found matching your search.
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
                            <?php if (($recipe['dish_role'] ?? 'main') === 'side'): ?>
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
<?php endif; ?>
