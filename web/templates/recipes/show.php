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
        const densityData = <?= json_encode($densityData ?? []) ?>;

        // --- 1. Unit Standards (US Customary to mL) ---
        const units = {
            'cup': 236.59, 'cups': 236.59, 'c': 236.59,
            'tablespoon': 14.79, 'tablespoons': 14.79, 'tbsp': 14.79, 'tbs': 14.79, 'T': 14.79,
            'teaspoon': 4.93, 'teaspoons': 4.93, 'tsp': 4.93, 't': 4.93,
            'gallon': 3785.41, 'gallons': 3785.41, 'gal': 3785.41,
            'quart': 946.35, 'quarts': 946.35, 'qt': 946.35,
            'pint': 473.18, 'pints': 473.18, 'pt': 473.18,
            'ounce': 29.57, 'ounces': 29.57, 'oz': 29.57,
            'pound': 453.59, 'pounds': 453.59, 'lb': 453.59, 'lbs': 453.59
        };

        // --- 2. Smart Unit Converter ---
        function optimizeUnit(amount, currentUnit) {
            const unitKey = currentUnit.toLowerCase().replace('.', '');
            const mlPerUnit = units[unitKey];

            if (!mlPerUnit) return { amount: amount, unit: currentUnit };

            const totalMl = amount * mlPerUnit;

            // Simple Logic: If < 0.25 cup (approx 4 tbsp), switch to Tbsp
            // If < 1 tbsp, switch to Tsp
            
            if (unitKey.includes('cup') && amount < 0.25) {
                const tbsp = totalMl / units['tbsp'];
                // Only switch if it's a nice number (whole or 0.5)
                if (Math.abs(Math.round(tbsp) - tbsp) < 0.2 || Math.abs((tbsp - 0.5) % 1) < 0.1) {
                    return { amount: parseFloat(tbsp.toFixed(1)), unit: 'tbsp' };
                }
            }
            
            return { amount: parseFloat(amount.toFixed(2)), unit: currentUnit };
        }

        // Unicode Fraction Map
        const vulgarFractions = {
            '½': 0.5, '⅓': 1 / 3, '⅔': 2 / 3, '¼': 0.25, '¾': 0.75,
            '⅕': 0.2, '⅖': 0.4, '⅗': 0.6, '⅘': 0.8,
            '⅙': 1 / 6, '⅚': 5 / 6, '⅛': 0.125, '⅜': 0.375, '⅝': 0.625, '⅞': 0.875
        };

        function parseQuantity(str) {
            // 1. Try Unicode Match First (e.g. "½")
            for (const [char, val] of Object.entries(vulgarFractions)) {
                if (str.includes(char)) {
                    // Handle "1½" (Mixed)
                    const parts = str.split(char);
                    const whole = parseFloat(parts[0]) || 0;
                    return whole + val;
                }
            }

            // 2. Try ASCII Fraction (e.g. "1/2", "1 1/2")
            if (str.includes('/')) {
                const parts = str.trim().split(/\s+/);
                let total = 0;
                for (let part of parts) {
                    if (part.includes('/')) {
                        const [num, den] = part.split('/').map(Number);
                        if (den !== 0) total += num / den;
                    } else {
                        total += parseFloat(part) || 0;
                    }
                }
                return total;
            }

            // 3. Fallback to float
            return parseFloat(str);
        }

        function formatQuantity(num) {
            // Close enough to whole number?
            if (Math.abs(Math.round(num) - num) < 0.05) return Math.round(num);

            // Close to common fractions?
            const fractions = [
                { val: 0.25, str: '¼' }, { val: 0.5, str: '½' }, { val: 0.75, str: '¾' },
                { val: 0.33, str: '⅓' }, { val: 0.66, str: '⅔' }, { val: 0.125, str: '⅛' }
            ];

            const whole = Math.floor(num);
            const decimal = num - whole;

            for (const frac of fractions) {
                if (Math.abs(decimal - frac.val) < 0.05) {
                    return (whole > 0 ? whole : '') + frac.str; // Return unicode 1½
                }
            }

            // Fallback to 2 decimals
            return parseFloat(num.toFixed(2));
        }

        function updateIngredients() {
            const target = parseFloat(scalerInput.value);
            if (!target || target <= 0) return;

            const ratio = target / baseServings;

            // Visual indicator
            scaleLabel.style.opacity = (target !== baseServings) ? '1' : '0';

            ingredientItems.forEach(item => {
                const originalText = item.dataset.original;

                // Matches start of string:
                // 1. "1 1/2" or "1/2" or "1.5" or "1" (ASCII)
                // 2. "1½" or "½" (Unicode)
                const numberRegex = /^([\d\s\/.,]+|[\d\s]*[½⅓⅔¼¾⅕⅖⅗⅘⅙⅚⅛⅜⅝⅞])+/;

                const match = originalText.match(numberRegex);

                if (match) {
                    const numberStr = match[0].trim();
                    // Skip if it looks like a range "1-2" (too complex for now)
                    if (numberStr.includes('-')) return;

                    const val = parseQuantity(numberStr);
                    if (!isNaN(val) && val > 0) {
                        const newVal = val * ratio;
                        
                        // Smart Unit Conversion
                        // Extract suffix (rest of string)
                        const suffix = originalText.substring(match[0].length).trim();
                        // Try to find the first word as the unit
                        const unitMatch = suffix.match(/^([a-zA-Z.]+)\s/);
                        
                        let finalVal = newVal;
                        let finalSuffix = suffix;

                        if (unitMatch) {
                            const originalUnit = unitMatch[1];
                            const optimized = optimizeUnit(newVal, originalUnit);
                            
                            finalVal = optimized.amount;
                            if (optimized.unit !== originalUnit) {
                                // Replace the unit in the suffix
                                finalSuffix = suffix.replace(originalUnit, optimized.unit);
                            }
                        }

                        const formattedVal = formatQuantity(finalVal);

                        // Replace only the number part at the start
                        item.innerText = formattedVal + " " + finalSuffix;
                        return;
                    }
                }
            });
        }

        scalerInput.addEventListener('input', updateIngredients);

        // Run once on load if default is different
        updateIngredients();
    });
</script>