<div class="row">
    <div class="col-md-12 mb-3">
        <?php if (!empty($queryParams['from_plan'])): ?>
            <a href="<?= url('/plans/' . h($queryParams['from_plan'])) ?>" class="btn btn-outline-secondary">&larr; Back to
                Meal
                Plan</a>
        <?php else: ?>
            <a href="<?= url('/recipes') ?>" class="btn btn-outline-secondary">&larr; Back to Recipes</a>
        <?php endif; ?>
    </div>
</div>

<div class="row">
    <div class="col-lg-8">
        <div class="card shadow-sm mb-4">
            <div class="card-body">
                <div class="d-flex justify-content-between align-items-start mb-3">
                    <h1 class="card-title display-6"><?= h($recipe['name']) ?></h1>
                    <span class="badge bg-secondary fs-6"><?= ucfirst($recipe['meal_type']) ?></span>
                </div>

                <?php if (!empty($recipe['description'])): ?>
                    <p class="lead text-muted fst-italic"><?= h($recipe['description']) ?></p>
                <?php endif; ?>

                <div class="row text-center my-4 py-3 bg-light rounded mx-1">
                    <div class="col-3 border-end">
                        <small class="text-muted d-block uppercase">Prep Time</small>
                        <strong><?= h($recipe['prep_time'] ?: '-') ?></strong>
                    </div>
                    <div class="col-3 border-end">
                        <small class="text-muted d-block uppercase">Cook Time</small>
                        <strong><?= h($recipe['cook_time'] ?: '-') ?></strong>
                    </div>
                    <div class="col-4 border-end">
                        <small class="text-muted d-block uppercase">Servings</small>
                        <div class="d-flex align-items-center justify-content-center gap-1">
                            <?php
                            $baseServes = (int) ($recipe['serves'] ?: 1);
                            $targetServes = isset($queryParams['serving_target']) ? (int) $queryParams['serving_target'] : $baseServes;
                            ?>
                            <input type="number" id="servingScaler"
                                class="form-control form-control-sm text-center p-0 fw-bold"
                                style="width: 40px; height: 24px;" value="<?= $targetServes ?>" min="1" max="50">
                            <span class="text-muted small">/ <?= $baseServes ?></span>
                        </div>
                    </div>
                    <div class="col-2">
                        <small class="text-muted d-block uppercase">Cal</small>
                        <strong><?= h($recipe['calories'] ?: '-') ?></strong>
                    </div>
                </div>

                <div class="mb-4">
                    <h4 class="border-bottom pb-2">Instructions</h4>
                    <?php if (!empty($recipe['instructions'])): ?>
                        <ol class="list-group list-group-numbered list-group-flush">
                            <?php foreach ($recipe['instructions'] as $step): ?>
                                <li class="list-group-item"><?= h($step) ?></li>
                            <?php endforeach; ?>
                        </ol>
                    <?php else: ?>
                        <p class="text-muted fst-italic">No instructions listed.</p>
                    <?php endif; ?>
                </div>

                <?php if (!empty($recipe['tips'])): ?>
                    <div class="alert alert-info">
                        <h5>💡 Tips & Notes</h5>
                        <ul class="mb-0">
                            <?php foreach ($recipe['tips'] as $tip): ?>
                                <li><?= h($tip) ?></li>
                            <?php endforeach; ?>
                        </ul>
                    </div>
                <?php endif; ?>
            </div>
        </div>
    </div>

    <div class="col-lg-4">
        <div class="card shadow-sm mb-4">
            <div class="card-header bg-success text-white d-flex justify-content-between align-items-center">
                <h5 class="card-title mb-0">Ingredients</h5>
                <small id="scaleLabel" class="badge bg-white text-success" style="opacity: 0">Scaled</small>
            </div>
            <ul class="list-group list-group-flush" id="ingredientList">
                <?php if (!empty($recipe['ingredients'])): ?>
                    <?php foreach ($recipe['ingredients'] as $ing): ?>
                        <li class="list-group-item ingredient-item" data-original="<?= h($ing['ingredient_text']) ?>">
                            <?= h($ing['ingredient_text']) ?>
                        </li>
                    <?php endforeach; ?>
                <?php else: ?>
                    <li class="list-group-item text-muted">No ingredients listed.</li>
                <?php endif; ?>
            </ul>
        </div>

        <div class="card shadow-sm mb-4">
            <div class="card-body">
                <h5 class="card-title">Details</h5>
                <dl class="row mb-0">
                    <dt class="col-sm-5">Chapter</dt>
                    <dd class="col-sm-7"><?= h($recipe['chapter'] ?: 'Unknown') ?></dd>

                    <dt class="col-sm-5">Page</dt>
                    <dd class="col-sm-7"><?= h($recipe['page_number'] ?: 'N/A') ?></dd>

                    <dt class="col-sm-5">Role</dt>
                    <dd class="col-sm-7"><?= ucfirst($recipe['dish_role']) ?></dd>
                </dl>
            </div>
        </div>

        <?php if (!empty($recipe['dietary_info'])): ?>
            <div class="card shadow-sm">
                <div class="card-body">
                    <h5 class="card-title">Dietary Info</h5>
                    <div>
                        <?php foreach ($recipe['dietary_info'] as $tag): ?>
                            <span class="badge bg-info text-dark me-1 mb-1"><?= h($tag) ?></span>
                        <?php endforeach; ?>
                    </div>
                </div>
            </div>
        <?php endif; ?>
    </div>
</div>
</div>

<script>
    document.addEventListener('DOMContentLoaded', function () {
        const scalerInput = document.getElementById('servingScaler');
        const ingredientItems = document.querySelectorAll('.ingredient-item');
        const scaleLabel = document.getElementById('scaleLabel');

        // Store Base Servings from PHP
        const baseServings = <?= $baseServes ?>;

        function updateIngredients() {
            const target = parseFloat(scalerInput.value);
            if (!target || target <= 0) return;

            const ratio = target / baseServings;

            // Visual indicator
            if (target !== baseServings) {
                scaleLabel.style.opacity = '1';
            } else {
                scaleLabel.style.opacity = '0';
            }

            ingredientItems.forEach(item => {
                const originalText = item.dataset.original;

                // Regex to match leading numbers/fractions
                // Matches: "1", "1.5", "1/2", "1-2", "1 - 2"
                // We want to replace the FIRST number found at the start.

                // Simplistic Decimal Scaler:
                // Look for leading float/int
                const decimalMatch = originalText.match(/^(\d+(\.\d+)?)\s/);

                if (decimalMatch) {
                    const val = parseFloat(decimalMatch[1]);
                    const newVal = Math.round((val * ratio) * 100) / 100; // Round to 2 decimals
                    item.innerText = originalText.replace(decimalMatch[1], newVal);
                    return;
                }

                // Allow Fractions? (Bonus, maybe later. For now just decimals)
                // Just update text color if we can't scale it?
            });
        }

        scalerInput.addEventListener('input', updateIngredients);

        // Run once on load if default is different
        updateIngredients();
    });
</script>