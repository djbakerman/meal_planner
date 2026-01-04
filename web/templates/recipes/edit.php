<div class="row mb-4">
    <div class="col-md-12">
        <a href="<?= url('/recipes/' . $recipe['id']) ?>"
            class="text-decoration-none text-muted mb-2 d-inline-block">&larr; Back
            to Recipe</a>
        <h1 class="display-5 fw-bold mb-0">Edit Recipe</h1>
    </div>
</div>

<div class="row">
    <div class="col-md-8">
        <div class="card shadow-sm">
            <div class="card-body">
                <form action="<?= url('/recipes/' . $recipe['id']) ?>" method="POST">
                    <input type="hidden" name="_METHOD" value="PUT">

                    <div class="mb-3">
                        <label for="name" class="form-label">Name</label>
                        <input type="text" class="form-control" id="name" name="name" value="<?= h($recipe['name']) ?>"
                            required>
                    </div>

                    <div class="mb-3">
                        <label for="description" class="form-label">Description</label>
                        <textarea class="form-control" id="description" name="description"
                            rows="3"><?= h($recipe['description']) ?></textarea>
                    </div>

                    <div class="row mb-3">
                        <div class="col-md-6">
                            <label for="meal_type" class="form-label">Meal Type</label>
                            <select class="form-select" id="meal_type" name="meal_type">
                                <option value="dinner" <?= $recipe['meal_type'] === 'dinner' ? 'selected' : '' ?>>Dinner
                                </option>
                                <option value="lunch" <?= $recipe['meal_type'] === 'lunch' ? 'selected' : '' ?>>Lunch
                                </option>
                                <option value="breakfast" <?= $recipe['meal_type'] === 'breakfast' ? 'selected' : '' ?>>
                                    Breakfast</option>
                                <option value="snack" <?= $recipe['meal_type'] === 'snack' ? 'selected' : '' ?>>Snack
                                </option>
                                <option value="dessert" <?= $recipe['meal_type'] === 'dessert' ? 'selected' : '' ?>>Dessert
                                </option>
                                <option value="any" <?= $recipe['meal_type'] === 'any' ? 'selected' : '' ?>>Any</option>
                            </select>
                        </div>
                        <div class="col-md-6">
                            <label for="dish_role" class="form-label">Dish Role</label>
                            <select class="form-select" id="dish_role" name="dish_role">
                                <option value="main" <?= $recipe['dish_role'] === 'main' ? 'selected' : '' ?>>Main Dish
                                </option>
                                <option value="side" <?= $recipe['dish_role'] === 'side' ? 'selected' : '' ?>>Side Dish
                                </option>
                                <option value="condiment" <?= $recipe['dish_role'] === 'condiment' ? 'selected' : '' ?>>
                                    Condiment</option>
                                <option value="unknown" <?= $recipe['dish_role'] === 'unknown' ? 'selected' : '' ?>>Unknown
                                </option>
                            </select>
                        </div>
                    </div>

                    <div class="row mb-3">
                        <div class="col-md-3">
                            <label for="prep_time" class="form-label">Prep Time</label>
                            <input type="text" class="form-control" id="prep_time" name="prep_time"
                                value="<?= h($recipe['prep_time']) ?>">
                        </div>
                        <div class="col-md-3">
                            <label for="cook_time" class="form-label">Cook Time</label>
                            <input type="text" class="form-control" id="cook_time" name="cook_time"
                                value="<?= h($recipe['cook_time']) ?>">
                        </div>
                        <div class="col-md-3">
                            <label for="serves" class="form-label">Serves</label>
                            <input type="text" class="form-control" id="serves" name="serves"
                                value="<?= h($recipe['serves']) ?>">
                        </div>
                        <div class="col-md-3">
                            <label for="calories" class="form-label">Calories</label>
                            <input type="text" class="form-control" id="calories" name="calories"
                                value="<?= h($recipe['calories']) ?>">
                        </div>
                    </div>

                    <div class="d-flex justify-content-between align-items-center mt-4 pt-3 border-top">
                        <a href="<?= url('/recipes/' . $recipe['id']) ?>" class="text-danger" data-bs-toggle="modal"
                            data-bs-target="#deleteRecipeModal">Delete Recipe</a>
                        <button type="submit" class="btn btn-primary">Save Changes</button>
                    </div>
                </form>
            </div>
        </div>
    </div>

    <div class="col-md-4">
        <div class="alert alert-info">
            <h5>Note</h5>
            <p>To edit ingredients or instructions, for now you'll need to re-import the catalog or manually edit the
                database. Full editor coming soon.</p>
        </div>
    </div>
</div>

<!-- Delete Modal -->
<div class="modal fade" id="deleteRecipeModal" tabindex="-1" aria-hidden="true">
    <div class="modal-dialog">
        <div class="modal-content">
            <div class="modal-header">
                <h5 class="modal-title">Delete Recipe?</h5>
                <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
            </div>
            <div class="modal-body">
                <p>Are you sure you want to delete <strong>
                        <?= h($recipe['name']) ?>
                    </strong>?</p>
                <p class="text-danger small">This cannot be undone.</p>
            </div>
            <div class="modal-footer">
                <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancel</button>
                <form action="<?= url('/recipes/' . $recipe['id'] . '/delete') ?>" method="POST">
                    <button type="submit" class="btn btn-danger">Yes, Delete</button>
                </form>
            </div>
        </div>
    </div>
</div>