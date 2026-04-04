<nav aria-label="breadcrumb" class="mb-4">
    <ol class="breadcrumb">
        <li class="breadcrumb-item"><a href="<?= url('/plans') ?>">Meal Plans</a></li>
        <li class="breadcrumb-item"><a href="<?= url('/plans/' . $planId) ?>">Plan</a></li>
        <li class="breadcrumb-item active">Grocery List</li>
    </ol>
</nav>

<div class="d-flex justify-content-between align-items-center mb-4">
    <h1>Grocery List</h1>
    <div class="btn-group">
        <a href="<?= url('/plans/' . $planId) ?>" class="btn btn-outline-secondary">Back to Plan</a>
        <button onclick="window.print()" class="btn btn-outline-primary">Print</button>
        <button onclick="shareList()" class="btn btn-outline-success">
            <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" class="bi bi-share me-1" viewBox="0 0 16 16">
                <path d="M13.5 1a1.5 1.5 0 1 0 0 3 1.5 1.5 0 0 0 0-3M11 2.5a2.5 2.5 0 1 1 .603 1.628l-6.718 3.12a2.5 2.5 0 0 1 0 1.504l6.718 3.12a2.5 2.5 0 1 1-.488.876l-6.718-3.12a2.5 2.5 0 1 1 0-3.256l6.718-3.12A2.5 2.5 0 0 1 11 2.5m-8.5 4a1.5 1.5 0 1 0 0 3 1.5 1.5 0 0 0 0-3m11 5.5a1.5 1.5 0 1 0 0 3 1.5 1.5 0 0 0 0-3"/>
            </svg>
            Share
        </button>
        <div class="btn-group" role="group">
            <button type="button" class="btn btn-outline-primary dropdown-toggle" data-bs-toggle="dropdown" aria-expanded="false">
                Apple Reminders
            </button>
            <ul class="dropdown-menu dropdown-menu-end">
                <li><button class="dropdown-item" onclick="runAppleShortcut()">Send to iOS Reminders</button></li>
                <li><hr class="dropdown-divider"></li>
                <li><button class="dropdown-item" data-bs-toggle="modal" data-bs-target="#shortcutHelpModal">How to setup shortcut...</button></li>
            </ul>
        </div>
    </div>
</div>

<?php if (empty($groceryList)): ?>
    <div class="alert alert-info">
        <p class="mb-2">Grocery list not yet generated.</p>
        <button type="button" class="btn btn-primary" hx-post="/plans/<?= $planId ?>/grocery" hx-target="body"
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
                            <li class="list-group-item interactive-grocery-item" onclick="toggleItem(event, this)">
                                <input type="checkbox" class="form-check-input me-2" id="item-<?= md5($item) ?>">
                                <label for="item-<?= md5($item) ?>" style="cursor: pointer;" class="w-100 mb-0">
                                    <?= e($item) ?>
                                </label>
                            </li>
                        <?php endforeach; ?>
                    </ul>
                </div>
            </div>
        <?php endforeach; ?>
    </div>

    <?php
    $shareText = "Grocery List\n\n";
    $shortcutText = "";
    foreach ($groceryList as $category => $items) {
        if (!empty($items)) {
            $shareText .= strtoupper($category) . "\n";
            foreach ($items as $item) {
                // For regular sharing, keep category headers
                $shareText .= "[ ] " . $item . "\n";
                // For reminders/shortcuts, just dump the raw items so they split properly into checklists
                $shortcutText .= $item . "\n";
            }
            $shareText .= "\n";
        }
    }
    $shareTextEncoded = json_encode(trim($shareText));
    $shortcutTextEncoded = urlencode(trim($shortcutText));
    ?>

    <!-- iOS Shortcut Help Modal -->
    <div class="modal fade" id="shortcutHelpModal" tabindex="-1" aria-labelledby="shortcutHelpModalLabel" aria-hidden="true">
      <div class="modal-dialog">
        <div class="modal-content">
          <div class="modal-header">
            <h5 class="modal-title" id="shortcutHelpModalLabel">Apple Shortcuts Setup</h5>
            <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
          </div>
          <div class="modal-body">
            <p>To add each ingredient as a standalone checkable item in the iOS Reminders app, follow these steps on your iPhone:</p>
            <ol>
                <li>Open the <strong>Shortcuts</strong> app.</li>
                <li>Tap <strong>+</strong> to create a new shortcut and name it exactly <code>Add Groceries</code>.</li>
                <li>Add the action <strong>Split Text</strong> and set it to split <code>Shortcut Input</code> by <code>New Lines</code>.</li>
                <li>Add the action <strong>Repeat with Each</strong> and set it to repeat with <code>Split Text</code>.</li>
                <li>Inside the repeat block, add the action <strong>Add New Reminder</strong>. Set it to add <code>Repeat Item</code> to your <code>Groceries</code> list.</li>
                <li>Tap <strong>Done</strong> to save the shortcut.</li>
            </ol>
            <p class="text-muted small mb-0">Once set up, the "Send to Apple Reminders" button will seamlessly push all items into your grocery list.</p>
          </div>
          <div class="modal-footer">
            <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Close</button>
          </div>
        </div>
      </div>
    </div>

    <script>
    const shareData = {
        title: 'Grocery List',
        text: <?= $shareTextEncoded ?>
    };

    async function shareList() {
        if (navigator.share) {
            try {
                await navigator.share(shareData);
            } catch (err) {
                console.log('Error sharing:', err);
            }
        } else {
            navigator.clipboard.writeText(shareData.text).then(() => {
                alert("List copied to clipboard! (Web Share not supported)");
            });
        }
    }

    function runAppleShortcut() {
        // Trigger the custom shortcut URL scheme
        const url = `shortcuts://run-shortcut?name=Add%20Groceries&input=text&text=<?= $shortcutTextEncoded ?>`;
        window.location.href = url;
    }

    function toggleItem(event, element) {
        // Prevent double toggling if they clicked the checkbox directly
        if (event.target.tagName !== 'INPUT') {
            const checkbox = element.querySelector('input[type="checkbox"]');
            checkbox.checked = !checkbox.checked;
        }
        
        // Update visual state
        const checkbox = element.querySelector('input[type="checkbox"]');
        if (checkbox.checked) {
            element.classList.add('checked-active');
        } else {
            element.classList.remove('checked-active');
        }
    }
    </script>

    <!-- Styles -->
    <style>
        /* Interactive Checkout Styles */
        .checked-active label {
            text-decoration: line-through;
            color: #6c757d;
        }
        
        .list-group-item {
            transition: background-color 0.2s ease, opacity 0.2s ease;
        }
        
        label {
            transition: color 0.2s ease;
        }

        .checked-active {
            background-color: #f8f9fa;
            opacity: 0.7;
        }

        @media print {

            .navbar,
            .breadcrumb,
            .btn-group,
            footer {
                display: none !important;
            }

            .card {
                break-inside: avoid;
            }

            .form-check-input {
                -webkit-print-color-adjust: exact;
                print-color-adjust: exact;
            }
        }
    </style>
<?php endif; ?>