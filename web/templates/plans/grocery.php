<nav aria-label="breadcrumb" class="mb-4">
    <ol class="breadcrumb">
        <li class="breadcrumb-item"><a href="/plans">Meal Plans</a></li>
        <li class="breadcrumb-item"><a href="/plans/<?= $planId ?>">Plan</a></li>
        <li class="breadcrumb-item active">Grocery List</li>
    </ol>
</nav>

<div class="d-flex justify-content-between align-items-center mb-4">
    <h1>Grocery List</h1>
    <div class="btn-group">
        <a href="/plans/<?= $planId ?>" class="btn btn-outline-secondary">Back to Plan</a>
        <button onclick="window.print()" class="btn btn-outline-primary">Print</button>
    </div>
</div>

<?php if (empty($groceryList)): ?>
    <div class="alert alert-info">
        <p class="mb-2">Grocery list not yet generated.</p>
        <button type="button"
                class="btn btn-primary"
                hx-post="/plans/<?= $planId ?>/grocery"
                hx-target="body"
                hx-swap="innerHTML">
            Generate Grocery List
        </button>
    </div>
<?php else: ?>
    <div class="row">
        <?php foreach ($groceryList as $category => $items): ?>
            <div class="col-md-6 mb-4">
                <div class="card">
                    <div class="card-header">
                        <h5 class="mb-0"><?= e(ucfirst($category)) ?></h5>
                    </div>
                    <ul class="list-group list-group-flush">
                        <?php foreach ($items as $item): ?>
                            <li class="list-group-item">
                                <input type="checkbox" class="form-check-input me-2" id="item-<?= md5($item) ?>">
                                <label for="item-<?= md5($item) ?>" style="cursor: pointer;">
                                    <?= e($item) ?>
                                </label>
                            </li>
                        <?php endforeach; ?>
                    </ul>
                </div>
            </div>
        <?php endforeach; ?>
    </div>

    <!-- Print Styles -->
    <style>
        @media print {
            .navbar, .breadcrumb, .btn-group, footer { display: none !important; }
            .card { break-inside: avoid; }
            .form-check-input { -webkit-print-color-adjust: exact; print-color-adjust: exact; }
        }
    </style>
<?php endif; ?>
