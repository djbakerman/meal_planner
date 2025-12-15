<h1 class="mb-4">Recipe Catalogs</h1>

<!-- Flash Messages -->
<?php if (!empty($flash)): ?>
    <?php foreach ($flash as $type => $messages): ?>
        <?php foreach ((array)$messages as $message): ?>
            <div class="alert alert-<?= $type === 'error' ? 'danger' : $type ?> alert-dismissible fade show" role="alert">
                <?= htmlspecialchars($message) ?>
                <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
            </div>
        <?php endforeach; ?>
    <?php endforeach; ?>
<?php endif; ?>

<!-- Import Form -->
<div class="card mb-4">
    <div class="card-header">
        <h5 class="mb-0">Import Catalog</h5>
    </div>
    <div class="card-body">
        <form action="/catalogs/import" method="post">
            <div class="row g-3 align-items-end">
                <div class="col-md-8">
                    <label for="file_path" class="form-label">JSON Catalog File Path</label>
                    <input type="text"
                           class="form-control"
                           id="file_path"
                           name="file_path"
                           placeholder="/path/to/cookbook_catalog.json"
                           required>
                    <div class="form-text">Enter the full path to a JSON catalog file created by recipe_cataloger.py</div>
                </div>
                <div class="col-md-4">
                    <button type="submit" class="btn btn-primary">Import Catalog</button>
                </div>
            </div>
        </form>
    </div>
</div>

<!-- Catalog List -->
<div class="card">
    <div class="card-header">
        <h5 class="mb-0">Imported Catalogs</h5>
    </div>

    <?php if (empty($catalogs)): ?>
        <div class="card-body">
            <p class="text-muted mb-0">No catalogs imported yet. Import a JSON catalog file to get started.</p>
        </div>
    <?php else: ?>
        <div class="table-responsive">
            <table class="table table-hover mb-0">
                <thead>
                    <tr>
                        <th>Name</th>
                        <th>Recipes</th>
                        <th>Model</th>
                        <th>Imported</th>
                        <th></th>
                    </tr>
                </thead>
                <tbody>
                    <?php foreach ($catalogs as $catalog): ?>
                        <tr>
                            <td>
                                <strong><?= e($catalog['name']) ?></strong>
                                <?php if (!empty($catalog['source_folder'])): ?>
                                    <br><small class="text-muted"><?= e($catalog['source_folder']) ?></small>
                                <?php endif; ?>
                            </td>
                            <td><?= $catalog['recipe_count'] ?? 0 ?> recipes</td>
                            <td><?= e($catalog['model_used'] ?? '-') ?></td>
                            <td><?= date('M j, Y', strtotime($catalog['created_at'])) ?></td>
                            <td>
                                <a href="/recipes?catalog=<?= $catalog['id'] ?>" class="btn btn-sm btn-outline-primary">
                                    View Recipes
                                </a>
                            </td>
                        </tr>
                    <?php endforeach; ?>
                </tbody>
            </table>
        </div>
    <?php endif; ?>
</div>
