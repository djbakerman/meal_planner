<div class="row justify-content-center">
    <div class="col-md-5">
        <div class="card mt-5">
            <div class="card-header">
                <h4 class="mb-0">Create Account</h4>
            </div>
            <div class="card-body">
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

                <form action="/register" method="post">
                    <div class="mb-3">
                        <label for="username" class="form-label">Username</label>
                        <input type="text"
                               class="form-control"
                               id="username"
                               name="username"
                               minlength="3"
                               required
                               autofocus>
                        <div class="form-text">At least 3 characters</div>
                    </div>

                    <div class="mb-3">
                        <label for="email" class="form-label">Email</label>
                        <input type="email"
                               class="form-control"
                               id="email"
                               name="email"
                               required>
                    </div>

                    <div class="mb-3">
                        <label for="password" class="form-label">Password</label>
                        <input type="password"
                               class="form-control"
                               id="password"
                               name="password"
                               minlength="6"
                               required>
                        <div class="form-text">At least 6 characters</div>
                    </div>

                    <div class="mb-3">
                        <label for="confirm_password" class="form-label">Confirm Password</label>
                        <input type="password"
                               class="form-control"
                               id="confirm_password"
                               name="confirm_password"
                               required>
                    </div>

                    <button type="submit" class="btn btn-primary w-100">Create Account</button>
                </form>
            </div>
            <div class="card-footer text-center">
                <span class="text-muted">Already have an account?</span>
                <a href="/login">Login</a>
            </div>
        </div>
    </div>
</div>
