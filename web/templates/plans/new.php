<div class="row justify-content-center">
    <div class="col-md-8 col-lg-6">
        <div class="card shadow-lg border-0">
            <div class="card-header bg-primary text-white p-4">
                <h2 class="h4 mb-0">✨ Generate New Meal Plan</h2>
            </div>
            <div class="card-body p-4">
                <form action="<?= url('/plans') ?>" method="POST">

                    <!-- SECTION 1: Scope & Filters -->
                    <div class="row mb-4">
                        <div class="col-md-6">
                            <label for="catalog" class="form-label fw-bold">Prioritize Catalog (Optional)</label>
                            <select class="form-select" id="catalog" name="catalog_ids[]" multiple size="4">
                                <option value="" selected>Any / All Catalogs</option>
                                <?php if (!empty($catalogs)): ?>
                                    <?php foreach ($catalogs as $catalog): ?>
                                        <option value="<?= $catalog['id'] ?>">
                                            <?= h($catalog['name']) ?> (<?= $catalog['recipe_count'] ?> recipes)
                                        </option>
                                    <?php endforeach; ?>
                                <?php endif; ?>
                            </select>
                            <div class="form-text">Hold Cmd/Ctrl to select multiple. Leave "Any" selected to search
                                everything.</div>
                        </div>
                        <div class="col-md-6">
                            <label class="form-label fw-bold">Exclude Ingredients</label>
                            <input type="text" class="form-control" name="excluded_ingredients"
                                placeholder="e.g. shrimp, peanuts, mushrooms">
                        </div>
                    </div>

                    <!-- SECTION 2: Meal Types -->
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

                    <hr class="my-4 text-muted opacity-25">

                    <!-- SECTION 3: Quantity & Structure -->
                    <div class="row mb-4">
                        <!-- Slider (Full Width) -->
                        <div class="col-12 mb-4">
                            <label class="form-label fw-bold">Number of Days / Recipes</label>
                            <div class="range-wrap">
                                <input type="range" class="form-range" min="1" max="14" step="1" id="recipeCount"
                                    name="recipe_count" value="5">
                                <div class="d-flex justify-content-between px-1 text-muted small user-select-none mb-2"
                                    style="font-size: 0.75rem; margin-top: -5px;">
                                    <?php for ($i = 1; $i <= 14; $i++): ?>
                                        <span
                                            onclick="document.getElementById('recipeCount').value=<?= $i ?>; document.getElementById('recipeCount').dispatchEvent(new Event('input'))"
                                            style="cursor:pointer; width: 20px; text-align: center;"><?= $i ?></span>
                                    <?php endfor; ?>
                                </div>
                                <div
                                    class="d-flex align-items-baseline justify-content-center text-primary fs-3 fw-bold">
                                    <output id="countOutput">5</output> <span class="ms-2">days</span>
                                </div>
                                <div class="form-text text-center mb-3">
                                    Plan will generate recipes for each selected meal type for this many days.
                                </div>

                                <!-- Real-time Preview -->
                                <div class="alert alert-info border-info d-flex justify-content-center align-items-center"
                                    id="planPreviewBox">
                                    <span class="fs-5 me-2">📊</span>
                                    <span id="planPreviewText">Generating <strong>5 meals</strong> (5 Days × 1
                                        Type)</span>
                                </div>
                            </div>
                        </div>

                        <!-- Plan Structure (Half or Full? Let's go Col-12 to afford text space) -->
                        <div class="col-12 mb-3">
                            <label class="form-label fw-bold">Plan Structure 🏗️</label>
                            <div class="d-flex flex-column flex-md-row gap-3">
                                <!-- Option 1: Strict (Default) -->
                                <div class="card-radio p-3 position-relative flex-fill">
                                    <input class="d-none" type="radio" name="use_cumulative_count" id="modeStrict"
                                        value="0" checked>
                                    <label class="cursor-pointer w-100 h-100 d-block m-0" for="modeStrict">
                                        <strong>Structured Meals</strong>
                                        <div class="text-muted small mt-1" id="strictDesc">Lunch + Dinner → 5 Lunch + 5
                                            Dinner meals</div>
                                    </label>
                                </div>

                                <!-- Option 2: Cumulative -->
                                <div class="card-radio p-3 position-relative flex-fill">
                                    <input class="d-none" type="radio" name="use_cumulative_count" id="modeFlex"
                                        value="1">
                                    <label class="cursor-pointer w-100 h-100 d-block m-0" for="modeFlex">
                                        <strong>Flexible Picks</strong>
                                        <div class="text-muted small mt-1" id="flexDesc">Lunch + Dinner → 5 meals total
                                            (mixed)</div>
                                    </label>
                                </div>
                            </div>
                        </div>

                        <!-- Target Servings (Col-12 or 6 centered?) -->
                        <div class="col-12 mt-2">
                            <label class="form-label fw-bold">Target Servings 🍽️</label>
                            <div class="d-flex align-items-center gap-3">
                                <div class="btn-group flex-fill" role="group">
                                    <input type="radio" class="btn-check" name="target_servings" id="servings1"
                                        value="1">
                                    <label class="btn btn-outline-primary" for="servings1">1</label>

                                    <input type="radio" class="btn-check" name="target_servings" id="servings2"
                                        value="2">
                                    <label class="btn btn-outline-primary" for="servings2">2</label>

                                    <input type="radio" class="btn-check" name="target_servings" id="servings3"
                                        value="3">
                                    <label class="btn btn-outline-primary" for="servings3">3</label>

                                    <input type="radio" class="btn-check" name="target_servings" id="servings4"
                                        value="4" checked>
                                    <label class="btn btn-outline-primary" for="servings4">4+</label>
                                </div>
                                <div class="form-text small m-0" style="max-width: 200px;">
                                    Shopping lists will auto-scale to this size.
                                </div>
                            </div>
                        </div>
                    </div>

                    <div class="d-grid gap-2 mt-5">
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
        border-radius: 8px;
        cursor: pointer;
        transition: all 0.2s;
    }

    .card-radio:hover {
        background-color: #f8f9fa;
        border-color: #adb5bd;
    }

    .card-radio:has(input:checked) {
        border-color: #0d6efd;
        background-color: #f0f7ff;
    }
</style>

<script>
    document.addEventListener('DOMContentLoaded', function () {
        const slider = document.getElementById('recipeCount');
        const output = document.getElementById('countOutput');
        const previewText = document.getElementById('planPreviewText');
        const typeCheckboxes = document.querySelectorAll('input[name^="meal_types"]');
        const modeRadios = document.querySelectorAll('input[name="use_cumulative_count"]');
        const strictDesc = document.getElementById('strictDesc');
        const flexDesc = document.getElementById('flexDesc');

        function updatePreview() {
            const days = parseInt(slider.value);
            output.textContent = days;

            // Find checked radio
            let isCumulative = false;
            modeRadios.forEach(r => {
                if (r.checked && r.value === "1") isCumulative = true;
            });

            // Count selected types & Get Names
            let typeCount = 0;
            let typeNames = [];
            typeCheckboxes.forEach(cb => {
                if (cb.checked) {
                    typeCount++;
                    // Get label text (sibling)
                    const labelText = cb.nextElementSibling.querySelector('span:last-child').innerText;
                    typeNames.push(labelText);
                }
            });

            // Update Descriptions Dynamically
            if (typeCount === 0) {
                strictDesc.innerText = "Select types to see example.";
                flexDesc.innerText = "Select types to see example.";
            } else {
                // Limit to 3 for display sanity if user selects all
                let displayNames = [...typeNames]; // copy
                if (displayNames.length > 3) {
                    displayNames = displayNames.slice(0, 3);
                    displayNames.push('etc');
                }
                const joined = displayNames.join(" + ");

                // Structured: "Lunch + Dinner -> 5 Lunch + 5 Dinner meals"
                const strictExample = displayNames.map(t => t === 'etc' ? '...' : `${days} ${t}`).join(" + ");
                strictDesc.innerText = `${joined} → ${strictExample}`;

                // Flexible: "Lunch + Dinner -> 5 meals total (mixed)"
                flexDesc.innerText = `${joined} → ${days} meals total (mixed)`;
            }

            // Calc Total
            let totalMeals = 0;
            let label = "";
            const typeLabel = typeCount === 1 ? "Type" : "Types";

            if (typeCount === 0) {
                // No type selected -> "Any" -> Always Total = Days
                totalMeals = days;
                label = `(${days} Days × Any Type)`;
            } else {
                if (isCumulative) {
                    // Total = Days (The slider value acts as Total Count)
                    totalMeals = days;
                    label = `(${days} Recipes Pool - Mixed options)`;
                } else {
                    // Total = Days * Types
                    totalMeals = days * typeCount;
                    label = `(${days} Days × ${typeCount} ${typeLabel})`;
                }
            }

            previewText.innerHTML = `Generating <strong>${totalMeals} meals</strong> ${label}`;
        }

        modeRadios.forEach(r => r.addEventListener('change', updatePreview));

        // Listeners
        slider.addEventListener('input', updatePreview);
        typeCheckboxes.forEach(cb => cb.addEventListener('change', updatePreview));

        // Init
        updatePreview();
    });
</script>