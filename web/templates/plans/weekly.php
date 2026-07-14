<div class="row justify-content-center">
    <div class="col-md-9 col-lg-7">
        <div class="card shadow-lg border-0">
            <div class="card-header bg-dark text-white p-4 d-flex align-items-center">
                <h2 class="h4 mb-0">📅 Weekly Builder — Macro-Aware Plan</h2>
                <a href="<?= url('/plans/new') ?>" class="btn btn-sm btn-outline-light ms-auto">Classic generator</a>
            </div>
            <div class="card-body p-4">

                <div class="alert alert-info small">
                    Builds a full 7-day grazer plan (three meals + three snack slots) against the 90-day
                    calorie ramp: weeks 1–2 start near current intake and climb ~150 kcal per week to the
                    Build-phase target. Protein floor is enforced first, calories second, variety third.
                </div>

                <form action="<?= url('/plans/weekly') ?>" method="POST"
                    onsubmit="return showWeeklyBuildOverlay(this.querySelector('button[type=submit]'));">

                    <div class="row mb-4">
                        <div class="col-md-6">
                            <label class="form-label fw-bold">Program Week (1–13)</label>
                            <?php $selWeek = $preselect_week ?? 1; ?>
                            <select class="form-select" name="week_number">
                                <?php for ($w = 1; $w <= 13; $w++):
                                    $phase = $w <= 4 ? 'Foundation' : ($w <= 8 ? 'Build' : ($w <= 12 ? 'Define' : 'Test Week'));
                                    $kcal = $w <= 2 ? 2300 : ($w == 3 ? 2450 : ($w == 4 ? 2600 : ($w == 5 ? 2700 : 2800)));
                                    ?>
                                    <option value="<?= $w ?>" <?= $w == $selWeek ? 'selected' : '' ?>>
                                        Week <?= $w ?> — <?= $phase ?> (<?= $kcal ?> kcal training days)
                                    </option>
                                <?php endfor; ?>
                            </select>
                            <div class="form-text">Drives the calorie ramp. Repeat a week if the jump feels fast.</div>
                        </div>
                        <div class="col-md-6">
                            <label class="form-label fw-bold">Mode</label>
                            <?php $selMode = $preselect_mode ?? 'variety'; ?>
                            <div class="form-check card-radio mb-2">
                                <input class="form-check-input" type="radio" name="mode" value="variety" id="modeVariety"
                                    <?= $selMode === 'variety' ? 'checked' : '' ?>>
                                <label class="form-check-label" for="modeVariety">
                                    🔄 <strong>Balanced</strong> — ~14 recipes, dinners roll to next-day lunch
                                </label>
                            </div>
                            <div class="form-check card-radio">
                                <input class="form-check-input" type="radio" name="mode" value="simple" id="modeSimple"
                                    <?= $selMode === 'simple' ? 'checked' : '' ?>>
                                <label class="form-check-label" for="modeSimple">
                                    🍗 <strong>Keep It Simple</strong> — small staple pool, batch-cook repeats
                                </label>
                            </div>
                        </div>
                    </div>

                    <div class="mb-4">
                        <label class="form-label fw-bold mb-2">Training Days</label>
                        <div class="d-flex flex-wrap gap-2">
                            <?php
                            $dayList = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'];
                            $defaultTraining = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday'];
                            foreach ($dayList as $d): ?>
                                <div class="form-check form-check-inline">
                                    <input class="form-check-input" type="checkbox" name="training_days[]"
                                        value="<?= $d ?>" id="td_<?= $d ?>" <?= in_array($d, $defaultTraining) ? 'checked' : '' ?>>
                                    <label class="form-check-label" for="td_<?= $d ?>"><?= substr($d, 0, 3) ?></label>
                                </div>
                            <?php endforeach; ?>
                        </div>
                        <div class="form-text">Rest days automatically run 250 kcal lighter.</div>
                    </div>

                    <div class="row mb-4">
                        <div class="col-md-4">
                            <label class="form-label fw-bold">Protein Target (g/day)</label>
                            <input type="number" class="form-control" name="protein_target" value="180" min="100" max="260">
                        </div>
                        <div class="col-md-4">
                            <label class="form-label fw-bold">Calorie Override</label>
                            <input type="number" class="form-control" name="kcal_override" placeholder="(use ramp)" min="1600" max="4000">
                            <div class="form-text">Leave blank to follow the ramp.</div>
                        </div>
                        <div class="col-md-4">
                            <label class="form-label fw-bold">Exclude Ingredients</label>
                            <input type="text" class="form-control" name="excluded_ingredients"
                                placeholder="e.g. shrimp, peanuts">
                        </div>
                    </div>

                    <div class="mb-4">
                        <label class="form-label fw-bold">Catalogs (Optional)</label>
                        <select class="form-select" name="catalog_ids[]" multiple size="4">
                            <option value="" selected>Any / All Catalogs</option>
                            <?php if (!empty($catalogs)): ?>
                                <?php foreach ($catalogs as $catalog): ?>
                                    <option value="<?= $catalog['id'] ?>">
                                        <?= h($catalog['name']) ?> (<?= $catalog['recipe_count'] ?> recipes)
                                    </option>
                                <?php endforeach; ?>
                            <?php endif; ?>
                        </select>
                        <div class="form-text">
                            Tip: include the <em>Builder Staples</em> catalog — its shakes and quick snacks are
                            what make the grazer slots and protein floor solvable.
                        </div>
                    </div>

                    <div class="form-check form-switch mb-4">
                        <input class="form-check-input" type="checkbox" name="use_llm" value="1" id="useLlm" checked>
                        <label class="form-check-label" for="useLlm">
                            Use AI to estimate macros for recipes missing them (first run only; results are cached)
                        </label>
                    </div>

                    <div class="d-grid">
                        <button type="submit" class="btn btn-dark btn-lg">Build My Week</button>
                    </div>
                </form>
            </div>
        </div>
    </div>
</div>

<script>
// Staged progress overlay: the build is one long backend call (longer on the
// first run, when missing macros get AI-estimated), so the bar eases toward
// 92% while the stages describe the actual pipeline.
function showWeeklyBuildOverlay(btn) {
    if (btn.disabled) return false;
    btn.disabled = true;
    btn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Building…';

    const steps = [
        'Loading your recipe catalogs…',
        'Filling in any missing macros…',
        'Balancing the cooking budget…',
        'Rolling dinners into next-day lunches…',
        'Fitting servings to the calorie ramp…',
        'Checking the protein floor…',
        'Setting the table…'
    ];
    const overlay = document.createElement('div');
    overlay.style.cssText = 'position:fixed;inset:0;background:rgba(15,23,42,0.72);z-index:2000;display:flex;align-items:center;justify-content:center;';
    overlay.innerHTML = `
        <div class="card shadow-lg border-0" style="max-width:420px;width:90%;">
            <div class="card-body p-4 text-center">
                <div class="spinner-border text-dark mb-3" role="status" aria-hidden="true"></div>
                <h5 class="mb-1">📅 Building your week</h5>
                <div id="wkStageMsg" class="text-muted small mb-3" style="min-height:1.5em;transition:opacity .3s;">${steps[0]}</div>
                <div class="progress mb-2" style="height:6px;">
                    <div id="wkProgressBar" class="progress-bar bg-dark" style="width:3%;transition:width 1s linear;"></div>
                </div>
                <div class="small text-muted"><span id="wkElapsed">0</span>s elapsed &middot; first run can take a few minutes</div>
            </div>
        </div>`;
    document.body.appendChild(overlay);

    let step = 0, elapsed = 0, progress = 3;
    const tick = setInterval(() => {
        elapsed += 1;
        document.getElementById('wkElapsed').textContent = elapsed;
        progress += Math.max(0.15, (92 - progress) * 0.018);
        document.getElementById('wkProgressBar').style.width = Math.min(92, progress) + '%';
    }, 1000);
    const rotate = setInterval(() => {
        step += 1;
        const el = document.getElementById('wkStageMsg');
        el.style.opacity = 0;
        setTimeout(() => { el.textContent = steps[step % steps.length]; el.style.opacity = 1; }, 300);
    }, 9000);

    // Submit via fetch: native form navigation suppresses repaints and froze
    // the overlay. The page stays alive; redirect when the build completes.
    const form = btn.closest('form');
    fetch(form.action, { method: 'POST', body: new FormData(form), credentials: 'same-origin' })
        .then(res => {
            clearInterval(tick); clearInterval(rotate);
            const bar = document.getElementById('wkProgressBar');
            const msg = document.getElementById('wkStageMsg');
            if (bar) { bar.style.transition = 'width .4s ease'; bar.style.width = '100%'; }
            if (msg) msg.textContent = 'Week built!';
            setTimeout(() => { window.location.href = res.url || window.location.href; }, 450);
        })
        .catch(() => {
            clearInterval(tick); clearInterval(rotate);
            setTimeout(() => { window.location.reload(); }, 450);
        });
    return false; // fetch handles submission; never navigate natively
}
</script>
