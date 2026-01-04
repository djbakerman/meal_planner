<div class="row mb-4">
    <div class="col-md-6">
        <a href="<?= url('/catalogs') ?>" class="text-decoration-none text-muted mb-2 d-inline-block">&larr; Back to
            Catalogs</a>
        <h1 class="display-5 fw-bold mb-0">
            <?= h($catalog['name']) ?>
        </h1>
        <small class="text-muted">Imported
            <?= date('M j, Y', strtotime($catalog['created_at'])) ?>
        </small>
    </div>
    <div class="col-md-6 text-md-end mt-3 mt-md-0">
        <button class="btn btn-outline-primary me-2" type="button" data-bs-toggle="collapse"
            data-bs-target="#renameForm">
            ✏️ Rename
        </button>
        <button class="btn btn-outline-danger" type="button" data-bs-toggle="modal" data-bs-target="#deleteModal">
            🗑️ Delete
        </button>
    </div>
</div>

<div class="collapse mb-4" id="renameForm">
    <div class="card card-body bg-light">
        <form action="<?= url('/catalogs/' . $catalog['id']) ?>" method="POST">
            <input type="hidden" name="_METHOD" value="PUT">
            <!-- Simulated PUT if using method spoofing, but we handled standard POST in controller for update logic usually, but let's stick to standard POST form with update action -->
            <!-- Actually Controller expects standard POST body for update method -->
            <label for="name" class="form-label">New Catalog Name</label>
            <div class="input-group">
                <input type="text" name="name" id="name" class="form-control" value="<?= h($catalog['name']) ?>"
                    required>
                <button class="btn btn-primary" type="submit">Save Name</button>
            </div>
        </form>
    </div>
</div>

<!-- Modal -->
<div class="modal fade" id="deleteModal" tabindex="-1" aria-hidden="true">
    <div class="modal-dialog">
        <div class="modal-content">
            <div class="modal-header">
                <h5 class="modal-title">Delete Catalog?</h5>
                <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
            </div>
            <div class="modal-body">
                <p>Are you sure you want to delete <strong>
                        <?= h($catalog['name']) ?>
                    </strong>?</p>
                <div class="alert alert-danger">
                    <strong>Warning:</strong> This will delete <strong>
                        <?= $catalog['recipe_count'] ?> recipes
                    </strong> associated with this catalog! This action cannot be undone.
                </div>
            </div>
            <div class="modal-footer">
                <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancel</button>
                <form action="<?= url('/catalogs/' . $catalog['id'] . '/delete') ?>" method="POST">
                    <button type="submit" class="btn btn-danger">Yes, Delete Everything</button>
                </form>
            </div>
        </div>
    </div>
</div>

<div class="row">
    <div class="col-md-4">
        <div class="card mb-4 shadow-sm">
            <div class="card-body">
                <h5 class="card-title">Catalog Stats</h5>
                <ul class="list-group list-group-flush">
                    <li class="list-group-item d-flex justify-content-between align-items-center">
                        Recipes
                        <span class="badge bg-primary rounded-pill">
                            <?= $catalog['recipe_count'] ?>
                        </span>
                    </li>
                    <li class="list-group-item d-flex justify-content-between align-items-center">
                        Model Used
                        <span class="badge bg-secondary">
                            <?= h($catalog['model_used'] ?? 'N/A') ?>
                        </span>
                    </li>
                    <li class="list-group-item">
                        <small class="text-muted d-block">Source</small>
                        <code><?= h(basename($catalog['source_folder'] ?? 'Unknown')) ?></code>
                    </li>
                </ul>
            </div>
        </div>
    </div>

    <div class="col-md-8">
        <div class="card shadow-sm">
            <div class="card-header bg-white d-flex justify-content-between align-items-center">
                <h5 class="mb-0">Recipes</h5>
                <a href="<?= url('/recipes?catalog_id=' . $catalog['id']) ?>"
                    class="btn btn-sm btn-outline-primary">Browse All
                    &rarr;</a>
            </div>
            <!-- We could list top 5 recent recipes here if API supported it, but link is enough for MVP -->
            <div class="card-body text-center py-5">
                <p class="text-muted">Head over to the Recipe Browser to view and manage recipes in this catalog.</p>
                <a href="<?= url('/recipes?catalog_id=' . $catalog['id']) ?>" class="btn btn-primary">Browse Recipes in
                    this
                    Catalog</a>
            </div>
        </div>
    </div>
</div>