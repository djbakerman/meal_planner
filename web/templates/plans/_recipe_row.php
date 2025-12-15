<?php
/**
 * Single recipe row partial - used for HTMX reroll responses
 */
$index = $position ?? 0;
?>
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
                hx-post="/plans/<?= $planId ?>/reroll/<?= $recipe['id'] ?>"
                hx-target="#recipe-row-<?= $recipe['id'] ?>"
                hx-swap="outerHTML"
                title="Replace with a different recipe">
            Reroll
        </button>
    </td>
</tr>
