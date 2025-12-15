<h1 class="mb-4">Generate New Meal Plan</h1>

<div class="row">
    <div class="col-md-6">
        <div class="card">
            <div class="card-body">
                <form action="/plans/generate" method="post">
                    <!-- Plan Name -->
                    <div class="mb-3">
                        <label for="name" class="form-label">Plan Name (optional)</label>
                        <input type="text"
                               class="form-control"
                               id="name"
                               name="name"
                               placeholder="e.g., Week of Dec 15">
                    </div>

                    <!-- Meal Types -->
                    <div class="mb-3">
                        <label class="form-label">Meal Types</label>
                        <div class="form-check">
                            <input class="form-check-input" type="checkbox" name="meal_types[]" value="breakfast" id="breakfast">
                            <label class="form-check-label" for="breakfast">Breakfast</label>
                        </div>
                        <div class="form-check">
                            <input class="form-check-input" type="checkbox" name="meal_types[]" value="lunch" id="lunch">
                            <label class="form-check-label" for="lunch">Lunch</label>
                        </div>
                        <div class="form-check">
                            <input class="form-check-input" type="checkbox" name="meal_types[]" value="dinner" id="dinner" checked>
                            <label class="form-check-label" for="dinner">Dinner</label>
                        </div>
                    </div>

                    <!-- Recipe Count -->
                    <div class="mb-3">
                        <label for="count" class="form-label">Number of Recipes</label>
                        <select class="form-select" id="count" name="count">
                            <option value="3">3 recipes</option>
                            <option value="5" selected>5 recipes</option>
                            <option value="7">7 recipes (one week)</option>
                            <option value="10">10 recipes</option>
                            <option value="14">14 recipes (two weeks)</option>
                        </select>
                    </div>

                    <!-- Submit -->
                    <button type="submit" class="btn btn-primary">
                        Generate Plan
                    </button>
                    <a href="/plans" class="btn btn-outline-secondary">Cancel</a>
                </form>
            </div>
        </div>
    </div>

    <div class="col-md-6">
        <div class="card bg-light">
            <div class="card-body">
                <h5 class="card-title">How it works</h5>
                <ul class="mb-0">
                    <li>Select the meal types you want to plan for</li>
                    <li>Choose how many recipes you need</li>
                    <li>We'll randomly select recipes from your catalogs</li>
                    <li>You can "reroll" any recipe you don't like</li>
                    <li>Generate a consolidated grocery list</li>
                    <li>Get an AI-powered meal prep plan</li>
                </ul>
            </div>
        </div>
    </div>
</div>
