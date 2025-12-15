<nav aria-label="breadcrumb" class="mb-4">
    <ol class="breadcrumb">
        <li class="breadcrumb-item"><a href="/plans">Meal Plans</a></li>
        <li class="breadcrumb-item"><a href="/plans/<?= $planId ?>">Plan</a></li>
        <li class="breadcrumb-item active">Prep Plan</li>
    </ol>
</nav>

<div class="d-flex justify-content-between align-items-center mb-4">
    <h1>Meal Prep Plan</h1>
    <div class="btn-group">
        <a href="/plans/<?= $planId ?>" class="btn btn-outline-secondary">Back to Plan</a>
        <button onclick="window.print()" class="btn btn-outline-primary">Print</button>
    </div>
</div>

<?php if (empty($prepPlan)): ?>
    <div class="alert alert-info">
        <p class="mb-2">Prep plan not yet generated.</p>
        <button type="button"
                class="btn btn-primary"
                hx-post="/plans/<?= $planId ?>/prep"
                hx-target="body"
                hx-swap="innerHTML">
            Generate Prep Plan
        </button>
    </div>
<?php else: ?>
    <!-- Advance Prep -->
    <?php if (!empty($prepPlan['advance'])): ?>
        <div class="card mb-4">
            <div class="card-header bg-primary text-white">
                <h5 class="mb-0">Advance Prep (1-2 Days Before)</h5>
            </div>
            <div class="card-body">
                <ul class="list-unstyled mb-0">
                    <?php foreach ($prepPlan['advance'] as $task): ?>
                        <li class="mb-2">
                            <input type="checkbox" class="form-check-input me-2">
                            <?= e($task) ?>
                        </li>
                    <?php endforeach; ?>
                </ul>
            </div>
        </div>
    <?php endif; ?>

    <!-- Day-of Prep -->
    <?php if (!empty($prepPlan['day_of'])): ?>
        <div class="card mb-4">
            <div class="card-header bg-warning text-dark">
                <h5 class="mb-0">Day-of Prep</h5>
            </div>
            <div class="card-body">
                <ul class="list-unstyled mb-0">
                    <?php foreach ($prepPlan['day_of'] as $task): ?>
                        <li class="mb-2">
                            <input type="checkbox" class="form-check-input me-2">
                            <?= e($task) ?>
                        </li>
                    <?php endforeach; ?>
                </ul>
            </div>
        </div>
    <?php endif; ?>

    <!-- Batched Tasks -->
    <?php if (!empty($prepPlan['batched'])): ?>
        <div class="card mb-4">
            <div class="card-header bg-info text-white">
                <h5 class="mb-0">Batched Tasks (Do Together)</h5>
            </div>
            <div class="card-body">
                <?php foreach ($prepPlan['batched'] as $batchName => $tasks): ?>
                    <h6 class="mt-3"><?= e($batchName) ?></h6>
                    <ul class="list-unstyled">
                        <?php foreach ($tasks as $task): ?>
                            <li class="mb-1">
                                <input type="checkbox" class="form-check-input me-2">
                                <?= e($task) ?>
                            </li>
                        <?php endforeach; ?>
                    </ul>
                <?php endforeach; ?>
            </div>
        </div>
    <?php endif; ?>

    <!-- Storage Notes -->
    <?php if (!empty($prepPlan['storage'])): ?>
        <div class="card mb-4">
            <div class="card-header">
                <h5 class="mb-0">Storage Notes</h5>
            </div>
            <div class="card-body">
                <ul class="mb-0">
                    <?php foreach ($prepPlan['storage'] as $note): ?>
                        <li><?= e($note) ?></li>
                    <?php endforeach; ?>
                </ul>
            </div>
        </div>
    <?php endif; ?>

    <!-- Print Styles -->
    <style>
        @media print {
            .navbar, .breadcrumb, .btn-group, footer { display: none !important; }
            .card { break-inside: avoid; }
        }
    </style>
<?php endif; ?>
