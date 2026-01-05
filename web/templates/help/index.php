<div class="row mb-5">
    <div class="col-lg-8 mx-auto">
        <h1 class="display-4 fw-bold mb-4">How to Use Meal Planner</h1>
        <p class="lead text-muted mb-5">Master your meal planning with this comprehensive guide to importing recipes,
            creating plans, and generating shopping lists.</p>

        <div class="d-grid gap-5">
            <!-- 1. Managing Catalogs -->
            <section>
                <div class="d-flex align-items-start gap-3">
                    <div class="bg-primary text-white rounded-circle d-flex align-items-center justify-content-center flex-shrink-0"
                        style="width: 40px; height: 40px; font-weight: bold;">1</div>
                    <div>
                        <h2 class="h3 fw-bold mb-3">Manage Catalogs</h2>
                        <p>Your journey starts with recipes. Use <strong>Catalogs</strong> to organize recipes from
                            different sources (e.g., "Web Scrape", "Grandma's Cookbook").
                            <br><span class="badge bg-info text-dark mt-2">Note: Login required to view/edit</span>
                        </p>
                        <ul class="list-unstyled">
                            <li class="mb-2">✅ <strong>Import:</strong> Upload <code>.json</code> recipe files directly
                                on the <a href="<?= url('/catalogs') ?>">Catalogs page</a>.</li>
                            <li class="mb-2">✅ <strong>Clean:</strong> The system automatically cleans up recipe names
                                (e.g., "GRILLED CHICKEN" &rarr; "Grilled Chicken") upon import.</li>
                            <li class="mb-2">✅ <strong>View:</strong> Click "View Details" on any catalog card to see
                                all recipes within it.</li>
                        </ul>
                    </div>
                </div>
            </section>

            <!-- 2. Creating Plans -->
            <section>
                <div class="d-flex align-items-start gap-3">
                    <div class="bg-success text-white rounded-circle d-flex align-items-center justify-content-center flex-shrink-0"
                        style="width: 40px; height: 40px; font-weight: bold;">2</div>
                    <div>
                        <h2 class="h3 fw-bold mb-3">Create Meal Plans</h2>
                        <p>Generate a structured plan for the week in seconds.</p>
                        <ul class="list-unstyled">
                            <li class="mb-2">🚀 <strong>New Plan:</strong> Click "Create New Plan" on the Home or Plans
                                page.</li>
                            <li class="mb-2">⚙️ <strong>Customize:</strong> Choose how many days, how many meals per day
                                (Dinner, Lunch, Breakfast), and which catalogs to pull from.</li>
                            <li class="mb-2">🧠 <strong>AI Powered:</strong> The system intelligently picks recipes
                                based on your preferences.</li>
                        </ul>
                    </div>
                </div>
            </section>

            <!-- 3. Refining Your Plan -->
            <section>
                <div class="d-flex align-items-start gap-3">
                    <div class="bg-info text-dark rounded-circle d-flex align-items-center justify-content-center flex-shrink-0"
                        style="width: 40px; height: 40px; font-weight: bold;">3</div>
                    <div>
                        <h2 class="h3 fw-bold mb-3">Refine & Perfect</h2>
                        <p>Don't like a suggestion? You have full control to swap it out.</p>
                        <div class="card bg-light border-0 p-3 mb-3">
                            <h6 class="fw-bold">Available Actions:</h6>
                            <ul class="mb-0">
                                <li><strong>✨ Swap Similar:</strong> Use AI to find a close match (e.g., swap Salmon for
                                    Trout).</li>
                                <li><strong>🎲 Swap Random:</strong> Surprise me! Replaces with a random dish of the
                                    same type.</li>
                                <li><strong>📖 From Catalog:</strong> Pick a specific source catalog for the
                                    replacement.</li>
                                <li><strong>🗑 Remove:</strong> Delete a meal if your day is too busy.</li>
                                <li><strong>➕ Add Recipe:</strong> Browse your library or add a random extra meal.</li>
                            </ul>
                        </div>
                    </div>
                </div>
            </section>

            <!-- 4. Lists & Prep -->
            <section>
                <div class="d-flex align-items-start gap-3">
                    <div class="bg-warning text-dark rounded-circle d-flex align-items-center justify-content-center flex-shrink-0"
                        style="width: 40px; height: 40px; font-weight: bold;">4</div>
                    <div>
                        <h2 class="h3 fw-bold mb-3">Shop & Prep</h2>
                        <p>Turn your plan into action with one click.</p>
                        <ul class="list-unstyled">
                            <li class="mb-2">🛒 <strong>Grocery List:</strong> Generates a consolidated shopping list,
                                combining ingredients (e.g., "2 onions" + "1 onion" = "3 onions").</li>
                            <li class="mb-2">🔪 <strong>Prep Plan:</strong> Creates a step-by-step guide on what to prep
                                ahead of time to make your week smoother.</li>
                        </ul>
                    </div>
                </div>
            </section>
        </div>

        <hr class="my-5">

        <div class="text-center">
            <h3 class="mb-3">Ready to get started?</h3>
            <div class="d-flex gap-2 justify-content-center">
                <a href="<?= url('/catalogs') ?>" class="btn btn-outline-primary">Manage Catalogs</a>
                <a href="<?= url('/plans') ?>" class="btn btn-primary">Go to Meal Plans</a>
            </div>
        </div>
    </div>
</div>