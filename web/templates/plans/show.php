<div class="alert alert-info border-info shadow-sm d-flex align-items-center mb-4" role="alert">
    <span class="fs-4 me-3">🍽️</span>
    <div>
        <strong>Smart Kitchen Assistant</strong>
        <div class="small">This plan is optimized to minimize total prep time and food waste across the week.</div>
    </div>
    <button type="button" class="btn-close ms-auto" data-bs-dismiss="alert" aria-label="Close"></button>
</div>

<div class="row align-items-center mb-4">
    <div class="col-md-6">
        <a href="<?= url('/plans') ?>" class="text-decoration-none text-muted mb-2 d-inline-block">&larr; All Plans</a>
        <h1 class="display-5 fw-bold mb-0">
            <span id="planNameDisplay"><?= h($plan['name']) ?></span>

            <?php if ($plan['is_public']): ?>
                <span class="badge bg-info text-dark fs-6 align-middle">Public</span>
            <?php endif; ?>

            <?php
            $currentUser = $_SESSION['user'] ?? null;
            $isOwner = $currentUser && ($currentUser['id'] == $plan['user_id']);
            ?>

            <?php if ($isOwner): ?>
                <a href="#" onclick="renamePlan()" class="text-decoration-none text-muted fs-6 align-middle ms-2"
                    title="Rename Plan">✏️</a>

                <form id="renameForm" action="<?= url('/plans/' . $plan['id'] . '/update') ?>" method="POST"
                    style="display:none;">
                    <input type="hidden" name="name" id="newNameInput">
                </form>
            <?php endif; ?>
        </h1>
        <small class="text-muted d-block mb-3">
            Created <?= date('M j, Y', strtotime($plan['created_at'])) ?>
        </small>

        <!-- Social Controls -->
        <div class="d-flex align-items-center gap-2">
            <!-- Share Toggle (Owner Only) -->
            <?php if ($isOwner): ?>
                <form action="<?= url('/plans/' . $plan['id'] . '/share') ?>" method="POST" class="d-inline" id="shareForm">
                    <input type="hidden" name="is_public" value="<?= $plan['is_public'] ? 0 : 1 ?>">
                    <input type="hidden" name="new_name" id="shareNameInput">

                    <button type="button" onclick="confirmShare(<?= $plan['is_public'] ?>)"
                        class="btn btn-outline-secondary rounded-pill">
                        <?= $plan['is_public'] ? '🔒 Make Private' : '🌍 Share to Community' ?>
                    </button>
                </form>
            <?php endif; ?>

            <!-- Like Button -->
            <form action="<?= url('/plans/' . $plan['id'] . '/like') ?>" method="POST" class="d-inline">
                <button type="submit" class="btn btn-outline-danger rounded-pill" title="Like this plan">
                    ❤️ <?= $plan['likes_count'] ?>
                </button>
            </form>
        </div>
    </div>
    <?php if ($isOwner): ?>
        <div class="col-md-6 text-md-end mt-3 mt-md-0 d-flex gap-2 justify-content-md-end">
            <!-- These buttons will be activated in Module 5 -->
            <form action="<?= url('/plans/' . $plan['id'] . '/grocery') ?>" method="POST"
                onsubmit="handleGeneratorSubmit(this.querySelector('button'), 'Generating List...');">
                <button type="submit" class="btn btn-success">
                    🛒 Grocery List
                </button>
            </form>
            <form action="<?= url('/plans/' . $plan['id'] . '/prep') ?>" method="POST"
                onsubmit="handleGeneratorSubmit(this.querySelector('button'), 'Writing Plan...');">
                <button type="submit" class="btn btn-info text-white">
                    🔪 Prep Plan
                </button>
            </form>
            <form action="<?= url('/plans/' . $plan['id'] . '/delete') ?>" method="POST"
                onsubmit="return confirm('Are you sure you want to delete this ENTIRE meal plan? This action cannot be undone.');">
                <button type="submit" class="btn btn-danger">
                    🗑 Delete
                </button>
            </form>
        </div>
    <?php endif; ?>
</div>

<div class="row">
    <!-- Recipes Column -->
    <div class="col-lg-8">
        <h4 class="mb-3">Selected Recipes</h4>
        <?php if (empty($plan['plan_recipes'])): ?>
            <p>No recipes in this plan.</p>
        <?php else: ?>
            <?php if ($isOwner): ?>
                <form action="<?= url('/plans/' . $plan['id'] . '/swap') ?>" method="POST" id="swapForm">
                    <input type="hidden" name="catalog_id" id="hiddenCatalogId" value="">

                    <!-- Unified Toolbar -->
                    <div class="card bg-light border-0 mb-3 p-3">
                        <!-- Active Exclusions Logic -->
                        <?php if (!empty($plan['excluded_ingredients'])): ?>
                            <div class="mb-3">
                                <small class="text-uppercase text-muted fw-bold"
                                    style="font-size: 0.75rem; letter-spacing: 1px;">Active Exclusions</small>
                                <div class="d-flex flex-wrap gap-2 mt-1">
                                    <?php foreach ($plan['excluded_ingredients'] as $ex): ?>
                                        <span class="badge bg-danger bg-opacity-10 text-danger border border-danger rounded-pill"
                                            title="These ingredients are strictly excluded from all swaps and regenerations.">
                                            🚫 <?= h(ucfirst($ex)) ?>
                                        </span>
                                    <?php endforeach; ?>
                                </div>
                            </div>
                        <?php endif; ?>

                        <div class="d-flex justify-content-between align-items-center">

                            <!-- LEFT: Add Actions -->
                            <div class="btn-group">
                                <button type="button" class="btn btn-primary dropdown-toggle" data-bs-toggle="dropdown"
                                    aria-expanded="false">
                                    ➕ Add Recipe
                                </button>
                                <ul class="dropdown-menu">
                                    <li>
                                        <a class="dropdown-item" href="<?= url('/recipes?add_to_plan=' . $plan['id']) ?>">
                                            🔍 Browse & Add...
                                        </a>
                                    </li>
                                    <li>
                                        <hr class="dropdown-divider">
                                    </li>
                                    <li>
                                        <button type="submit" formaction="<?= url('/plans/' . $plan['id'] . '/add') ?>"
                                            name="random" value="true" class="dropdown-item">
                                            🎲 Add Random Surprise
                                        </button>
                                    </li>
                                    <?php if (!empty($catalogs)): ?>
                                        <li>
                                            <hr class="dropdown-divider">
                                        </li>
                                        <li>
                                            <h6 class="dropdown-header">📖 Add From Catalog</h6>
                                        </li>
                                        <?php foreach ($catalogs as $cat): ?>
                                            <li>
                                                <button type="submit" formaction="<?= url('/plans/' . $plan['id'] . '/add') ?>"
                                                    name="random" value="true" class="dropdown-item"
                                                    onclick="this.form.catalog_id.value='<?= $cat['id'] ?>';">
                                                    <?= h($cat['name']) ?>
                                                </button>
                                            </li>
                                        <?php endforeach; ?>
                                    <?php endif; ?>
                                </ul>
                            </div>

                            <!-- RIGHT: Selection Actions -->
                            <div class="d-flex align-items-center gap-2">
                                <small class="text-muted d-none d-md-block me-2">Selected:</small>

                                <!-- Swap Dropdown -->
                                <div class="btn-group">
                                    <button type="button" class="btn btn-outline-primary dropdown-toggle"
                                        data-bs-toggle="dropdown" aria-expanded="false">
                                        🔁 Swap
                                    </button>
                                    <ul class="dropdown-menu dropdown-menu-end">
                                        <li>
                                            <button type="submit" name="mode" value="quick" class="dropdown-item">
                                                ⚡ <strong>Quick Swap</strong> <span
                                                    class="text-muted small ms-2">(Default)</span>
                                            </button>
                                        </li>
                                        <li>
                                            <button type="submit" name="mode" value="similar" class="dropdown-item">
                                                🧠 Find Similar
                                            </button>
                                        </li>
                                        <li>
                                            <button type="submit" name="mode" value="flexible" class="dropdown-item">
                                                🧩 Be Flexible <span class="text-muted small ms-2">(Ignore Type)</span>
                                            </button>
                                        </li>
                                        <?php if (!empty($catalogs)): ?>
                                            <li>
                                                <hr class="dropdown-divider">
                                            </li>
                                            <li>
                                                <h6 class="dropdown-header">📖 Pick from Catalog</h6>
                                            </li>
                                            <?php foreach ($catalogs as $cat): ?>
                                                <li>
                                                    <button type="submit" name="mode" value="catalog" class="dropdown-item"
                                                        onclick="document.getElementById('hiddenCatalogId').value='<?= $cat['id'] ?>'">
                                                        <?= h($cat['name']) ?>
                                                    </button>
                                                </li>
                                            <?php endforeach; ?>
                                        <?php endif; ?>
                                    </ul>
                                </div>

                                <!-- Remove Button -->
                                <button type="submit" formaction="<?= url('/plans/' . $plan['id'] . '/remove') ?>"
                                    class="btn btn-outline-danger" title="Remove selected recipes">
                                    🗑 Remove
                                </button>
                            </div>
                        </div>
                    </div>

                    <div class="list-group shadow-sm mb-5">
                        <?php foreach ($plan['plan_recipes'] as $pr):
                            $recipe = $pr['recipe']; // Nested object from API
                            ?>
                            <label class="list-group-item list-group-item-action p-3 d-flex gap-3 align-items-center"
                                style="cursor: pointer;">
                                <input class="form-check-input flex-shrink-0" type="checkbox" name="recipe_ids[]"
                                    value="<?= $recipe['id'] ?>" style="font-size: 1.3em;">

                                <div class="d-flex w-100 justify-content-between align-items-center">
                                    <div>
                                        <h5 class="mb-1">
                                            <a href="<?= url('/recipes/' . $recipe['id'] . '?from_plan=' . $plan['id'] . '&serving_target=' . ($plan['target_servings'] ?? 4)) ?>"
                                                class="text-decoration-none text-dark">
                                                <?= h($recipe['name']) ?>
                                            </a>
                                        </h5>
                                        <div class="text-muted small">
                                            <span
                                                class="badge bg-light text-dark border me-1"><?= ucfirst($recipe['meal_type']) ?></span>
                                            <?php if (!empty($recipe['calories'])): ?>
                                                <span class="badge bg-danger bg-opacity-10 text-danger border border-danger me-1">
                                                    🔥 <?= h($recipe['calories']) ?>
                                                </span>
                                            <?php endif; ?>
                                            Using: <?= h($recipe['dish_role']) ?>
                                        </div>
                                    </div>
                                </div>
                            </label>
                            <?php if (!empty($recipe['sub_recipes'])): ?>
                                <?php foreach ($recipe['sub_recipes'] as $sub): ?>
                                    <div
                                        class="list-group-item list-group-item-light p-2 ps-5 border-top-0 text-muted d-flex align-items-center">
                                        <span class="me-2" style="opacity: 0.5;">↳</span>
                                        <div>
                                            <strong><?= h($sub['name']) ?></strong>
                                            <span class="badge bg-secondary bg-opacity-10 text-secondary border border-secondary ms-2"
                                                style="font-size: 0.7em;">Component</span>
                                        </div>
                                    </div>
                                <?php endforeach; ?>
                            <?php endif; ?>
                        <?php endforeach; ?>
                    </div>
                </form>
            <?php else: ?>
                <div class="alert alert-light border shadow-sm mb-4">
                    <div class="d-flex align-items-center justify-content-between">
                        <div>
                            <strong>Want to customize this plan?</strong>
                            <p class="mb-0 text-muted">Fork this plan to your account to add or swap recipes.</p>
                        </div>
                        <form action="<?= url('/plans/' . $plan['id'] . '/clone') ?>" method="POST">
                            <button type="submit" class="btn btn-primary">
                                🔱 Copy to My Plans
                            </button>
                        </form>
                    </div>
                </div>

                <div class="list-group shadow-sm mb-5">
                    <?php foreach ($plan['plan_recipes'] as $pr):
                        $recipe = $pr['recipe'];
                        ?>
                        <div class="list-group-item p-3 d-flex gap-3 align-items-center">
                            <!-- No Checkbox for non-owners -->
                            <div class="d-flex w-100 justify-content-between align-items-center">
                                <div>
                                    <h5 class="mb-1">
                                        <a href="<?= url('/recipes/' . $recipe['id'] . '?from_plan=' . $plan['id'] . '&serving_target=' . ($plan['target_servings'] ?? 4)) ?>"
                                            class="text-decoration-none text-dark">
                                            <?= h($recipe['name']) ?>
                                        </a>
                                    </h5>
                                    <div class="text-muted small">
                                        <span
                                            class="badge bg-light text-dark border me-1"><?= ucfirst($recipe['meal_type']) ?></span>
                                        <?php if (!empty($recipe['calories'])): ?>
                                            <span class="badge bg-danger bg-opacity-10 text-danger border border-danger me-1">
                                                🔥 <?= h($recipe['calories']) ?>
                                            </span>
                                        <?php endif; ?>
                                        Using: <?= h($recipe['dish_role']) ?>
                                    </div>
                                </div>
                            </div>
                        </div>
                        <?php if (!empty($recipe['sub_recipes'])): ?>
                            <?php foreach ($recipe['sub_recipes'] as $sub): ?>
                                <div
                                    class="list-group-item list-group-item-light p-2 ps-5 border-top-0 text-muted d-flex align-items-center">
                                    <span class="me-2" style="opacity: 0.5;">↳</span>
                                    <div>
                                        <strong><?= h($sub['name']) ?></strong>
                                        <span class="badge bg-secondary bg-opacity-10 text-secondary border border-secondary ms-2"
                                            style="font-size: 0.7em;">Component</span>
                                    </div>
                                </div>
                            <?php endforeach; ?>
                        <?php endif; ?>
                    <?php endforeach; ?>
                </div>
            <?php endif; ?>
        <?php endif; ?>
    </div>

    <!-- AI Output Column (Placeholders for Module 5) -->
    <div class="col-lg-4">
        <?php if (!empty($plan['grocery_list'])): ?>
            <?php
            $rawContent = $plan['grocery_list']['content'] ?? '';
            $lines = explode("\n", $rawContent);
            $groceryHtml = "";
            $rawItemsForShortcuts = "";

            foreach ($lines as $line) {
                $tLine = trim($line);
                if ($tLine === '') {
                    continue;
                } elseif (preg_match('/^(?:-\s*\[\s*\]|\[\s*\]|-|□|\*)\s*(.+)$/u', $tLine, $matches)) {
                    $cleanItem = h(trim($matches[1]));
                    $rawItemsForShortcuts .= trim($matches[1]) . "\n";
                    $groceryHtml .= '<label class="grocery-item d-flex align-items-start mb-2 rounded" style="cursor:pointer; transition: all 0.2s;" onclick="toggleGroceryItem(event, this)"><input type="checkbox" class="form-check-input me-2 mt-1 flex-shrink-0"> <span class="grocery-text">' . $cleanItem . "</span></label>";
                } else {
                    $cleanHeader = trim(str_replace(['#', '*'], '', $tLine));
                    $groceryHtml .= '<h6 class="mt-3 mb-2 fw-bold text-success border-bottom pb-1">' . h($cleanHeader) . '</h6>';
                }
            }
            $shareTextEncoded = json_encode($rawContent);
            $shortcutTextEncoded = urlencode(trim($rawItemsForShortcuts));
            ?>
            <div class="card shadow-sm mb-4 border-success">
                <div class="card-header bg-success text-white d-flex justify-content-between align-items-center">
                    <span>🛒 Grocery List</span>
                    <div class="btn-group btn-group-sm">
                        <button onclick="shareGrocery()" class="btn btn-light" title="Share List">
                            <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" fill="currentColor" class="bi bi-share" viewBox="0 0 16 16">
                                <path d="M13.5 1a1.5 1.5 0 1 0 0 3 1.5 1.5 0 0 0 0-3M11 2.5a2.5 2.5 0 1 1 .603 1.628l-6.718 3.12a2.5 2.5 0 0 1 0 1.504l6.718 3.12a2.5 2.5 0 1 1-.488.876l-6.718-3.12a2.5 2.5 0 1 1 0-3.256l6.718-3.12A2.5 2.5 0 0 1 11 2.5m-8.5 4a1.5 1.5 0 1 0 0 3 1.5 1.5 0 0 0 0-3m11 5.5a1.5 1.5 0 1 0 0 3 1.5 1.5 0 0 0 0-3"/>
                            </svg>
                        </button>
                        <button onclick="runAppleShortcut()" class="btn btn-light" title="Send to iOS Reminders">
                            Reminders
                        </button>
                    </div>
                </div>
                <div class="card-body">
                    <div class="small mb-0" style="font-family: inherit;">
                        <?= $groceryHtml ?>
                    </div>
                </div>
            </div>
            
            <script>
            function toggleGroceryItem(event, element) {
                if (event.target.tagName !== 'INPUT') {
                    const checkbox = element.querySelector('input[type="checkbox"]');
                    if (checkbox) checkbox.checked = !checkbox.checked;
                }
                const checkbox = element.querySelector('input[type="checkbox"]');
                const textSpan = element.querySelector('.grocery-text');
                if (checkbox && checkbox.checked) {
                    element.style.opacity = '0.5';
                    element.style.backgroundColor = '#f8f9fa';
                    if (textSpan) textSpan.style.textDecoration = 'line-through';
                } else {
                    element.style.opacity = '1';
                    element.style.backgroundColor = 'transparent';
                    if (textSpan) textSpan.style.textDecoration = 'none';
                }
            }

            function shareGrocery() {
                const shareData = {
                    title: 'Grocery List',
                    text: <?= $shareTextEncoded ?>
                };
                if (navigator.share) {
                    navigator.share(shareData).catch(err => console.log(err));
                } else {
                    navigator.clipboard.writeText(shareData.text).then(() => alert("List copied to clipboard!"));
                }
            }

            function runAppleShortcut() {
                if(confirm("This will trigger a shortcut named 'Add Groceries' on your iPhone if installed. Continue?")) {
                    window.location.href = `shortcuts://run-shortcut?name=Add%20Groceries&input=text&text=<?= $shortcutTextEncoded ?>`;
                }
            }
            </script>
        <?php endif; ?>

        <?php if (!empty($plan['prep_plan'])): ?>
            <div class="card shadow-sm border-info">
                <div class="card-header bg-info text-white">
                    🔪 Prep Plan (Ready)
                </div>
                <div class="card-body">
                    <pre class="small mb-0"
                        style="white-space: pre-wrap; font-family: inherit;"><?= h($plan['prep_plan']['content'] ?? 'Error loading content') ?></pre>
                </div>
            </div>
        <?php endif; ?>

        <div class="alert alert-light border">
            <h5>💡 Plan Stats</h5>
            <ul class="list-unstyled mb-0">
                <li><strong>Meals:</strong> <?= $plan['recipe_count'] ?></li>
                <li>
                    <strong>Servings:</strong>
                    <span id="servingsDisplay"><?= $plan['target_servings'] ?? 4 ?></span> ppl
                    <?php if ($isOwner): ?>
                        <a href="#" onclick="updateServings()" class="text-decoration-none text-muted small ms-1"
                            title="Change target servings">✏️</a>
                    <?php endif; ?>
                </li>
                <?php if ($isOwner): ?>
                    <form id="updateServingsForm" action="<?= url('/plans/' . $plan['id'] . '/update') ?>" method="POST"
                        style="display:none;">
                        <input type="number" name="target_servings" id="newServingsInput">
                    </form>
                <?php endif; ?>
                <li><strong>Types:</strong> <?= implode(', ', array_map('ucfirst', $plan['meal_types'] ?? [])) ?></li>
            </ul>
        </div>


    </div>
</div>

<script>
    function renamePlan() {
        const currentName = document.getElementById('planNameDisplay').innerText;
        const newName = prompt("Rename your meal plan:", currentName);

        if (newName && newName.trim() !== "" && newName !== currentName) {
            document.getElementById('newNameInput').value = newName;
            document.getElementById('renameForm').submit();
        }
    }

    function updateServings() {
        const current = document.getElementById('servingsDisplay').innerText;
        const newServings = prompt("Change target servings (Lists will be invalidated):", current);

        if (newServings && newServings.trim() !== "" && newServings !== current) {
            const val = parseInt(newServings);
            if (isNaN(val) || val < 1) {
                alert("Please enter a valid number (1+).");
                return;
            }
            document.getElementById('newServingsInput').value = val;
            document.getElementById('updateServingsForm').submit();
        }
    }

    function confirmShare(isWaitPrivate) {
        const form = document.getElementById('shareForm');

        if (isWaitPrivate) {
            // Currently Public -> Making Private
            if (confirm("Are you sure you want to make this plan private? It will disappear from the Community page.")) {
                form.submit();
            }
        } else {
            // Currently Private -> Making Public
            const currentName = document.getElementById('planNameDisplay').innerText;
            const publicName = prompt("You are sharing this to the community! \n\nEnter a unique name for your plan (or keep as is):", currentName);

            if (publicName !== null) {
                // If user clicked OK (even if empty, though we should fallback)
                const finalName = publicName.trim() === "" ? currentName : publicName;
                document.getElementById('shareNameInput').value = finalName;
                form.submit();
            }
        }
    }


    function handleGeneratorSubmit(btn, loadingText) {
        // Prevent double clicks
        if (btn.disabled) return false;

        // Save original text if needed (though page will reload)
        const originalText = btn.innerHTML;

        // Update UI
        btn.disabled = true;
        btn.innerHTML = `<span class="spinner-border spinner-border-sm me-2" role="status" aria-hidden="true"></span>${loadingText}`;

        // Allow form submission to proceed
        return true;
    }
</script>