<div class="row justify-content-center">
    <div class="col-md-8 col-lg-6">
        <div class="card shadow-lg border-0">
            <div class="card-header bg-primary text-white p-4">
                <h2 class="h4 mb-0">✨ Generate New Meal Plan</h2>
            </div>
            <div class="card-body p-4">
                <form action="<?= url('/plans') ?>" method="POST">

                    <div class="mb-4">
                        <label class="form-label fw-bold">Number of Days</label>
                        <div class="range-wrap">
                            <input type="range" class="form-range" min="1" max="14" step="1" id="recipeCount"
                                name="recipe_count" value="5" oninput="countOutput.value = recipeCount.value">
                            <div class="text-center fw-bold text-primary fs-3">
                                <output id="countOutput">5</output> days
                            </div>
                            <div class="form-text text-center">
                                Plan will generate recipes for each selected meal type for this many days.
                            </div>
                        </div>
                    </div>

                    <div class="row mb-4">
                        <div class="col-md-6">
                            <label class="form-label fw-bold">Filter by Catalog</label>
                            <select class="form-select" name="catalog_id">
                                <option value="">📚 All Recipes</option>
                                <?php if (!empty($catalogs)): ?>
                                    <?php foreach ($catalogs as $cat): ?>
                                        <option value="<?= $cat['id'] ?>"><?= h($cat['name']) ?></option>
                                    <?php endforeach; ?>
                                <?php endif; ?>
                            </select>
                        </div>
                        <div class="col-md-6">
                            <label class="form-label fw-bold">Exclude Ingredients</label>
                            <input type="text" class="form-control" name="excluded_ingredients"
                                placeholder="e.g. shrimp, peanuts, mushrooms">
                        </div>
                    </div>

                    <div class="mb-4">
                        <label class="form-label fw-bold mb-2">Include Meal Types</label>
                        <div class="row g-3">
                            <?php
                            $types = ['dinner' => '🍛', 'lunch' => '🥪', 'breakfast' => '🍳', 'dessert' => '🍰', 'snack' => '🍎'];
                            foreach ($types as $key => $icon):
                                $checked = $key === 'dinner' ? 'checked' : '';
                                ?>
                                <div class="col-6">
                                    <div class="form-check card-radio">
                                        <input class="form-check-input" type="checkbox" name="meal_types[<?= $key ?>]"
                                            value="1" id="type_<?= $key ?>" <?= $checked ?>>
                                        <label class="form-check-label d-flex align-items-center gap-2"
                                            for="type_<?= $key ?>">
                                            <span class="fs-5">
                                                <?= $icon ?>
                                            </span>
                                            <span>
                                                <?= ucfirst($key) ?>
                                            </span>
                                        </label>
                                    </div>
                                </div>
                            <?php endforeach; ?>
                        </div>
                    </div>

                    <div class="d-grid gap-2">
                        <button type="submit" class="btn btn-primary btn-lg py-3">
                            Generate Plan 🚀
                        </button>
                        <a href="<?= url('/plans') ?>" class="btn btn-link text-muted">Cancel</a>
                    </div>
                </form>
            </div>
        </div>
    </div>
</div>

<style>
    /* Simple styling for the radio cards looks nice */
    .card-radio .form-check-input {
        float: right;
    }

    .card-radio {
        border: 1px solid #dee2e6;
        padding: 10px 15px;
        border-radius: 8px;
        cursor: pointer;
        transition: all 0.2s;
    }

    .card-radio:hover {
        background-color: #f8f9fa;
        border-color: #adb5bd;
    }

    .card-radio:has(.form-check-input:checked) {
        border-color: #0d6efd;
        background-color: #f0f7ff;
    }
</style>