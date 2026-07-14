# Recipe Toolkit

A suite of Python tools for extracting recipes from cookbook images, analyzing extraction quality, and meal planning with AI-generated grocery lists and prep plans.

## Overview

| Tool | Purpose |
|------|---------|
| `recipe_cataloger.py` | Extract recipes from cookbook images using vision AI (Ollama or Claude) |
| `page_analyzer.py` | Analyze catalogs for missed extractions and reprocess failures |
| `meal_planner.py` | Random meal planning with AI-consolidated grocery lists and prep plans |

---

## Installation

### Requirements

```bash
pip install requests
```

### AI Backend Options

**Option 1: Ollama (Local, Free)**
```bash
# Install Ollama from https://ollama.ai
ollama pull llava           # Basic vision model
ollama pull qwen2-vl:8b     # Better quality
ollama pull llama3.2        # For text-only tasks
```

**Option 2: Claude API (Cloud, Paid)**
```bash
export ANTHROPIC_API_KEY="sk-ant-api03-..."
# Get key from: https://console.anthropic.com/api-keys
```

---

## Recipe Cataloger

Extract recipes from cookbook page images into a searchable JSON catalog.

### Basic Usage

```bash
# Process a folder of cookbook images
python recipe_cataloger.py /path/to/images/ -m qwen2-vl:8b

# Process with Claude (better accuracy)
python recipe_cataloger.py /path/to/images/ -m claude-sonnet-4-20250514

# Use backup model for large files (Claude has 5MB limit)
python recipe_cataloger.py /path/to/images/ -m claude-sonnet-4-20250514 --backup-model qwen2-vl:8b

# Sort by modification date instead of filename (useful for screenshots)
python recipe_cataloger.py /path/to/images/ -m claude-sonnet-4-20250514 --sort-by date
```

### Single File Mode

```bash
# Test extraction on a single image
python recipe_cataloger.py -f /path/to/image.png -m claude-sonnet-4-20250514

# With debug diagnostics (analyzes why extraction might fail)
python recipe_cataloger.py -f /path/to/image.png -m claude-sonnet-4-20250514 --debug
```

### Multi-Page Recipe Mode

For recipes that span multiple pages, pass the files in order:

```bash
# Process 2 pages of a recipe that continues
python recipe_cataloger.py -f page1.png page2.png -m claude-sonnet-4-20250514

# Process 3 pages and append to existing catalog
python recipe_cataloger.py -f page1.png page2.png page3.png -m claude-sonnet-4-20250514 --append-to recipe_catalog.json

# With chapter context
python recipe_cataloger.py -f page1.png page2.png --chapter-title "Main Dishes" -m claude-sonnet-4-20250514
```

The multi-file mode:
- Processes files in the order provided
- Automatically handles recipe continuations between pages
- Uses page numbers to validate correct ordering
- Combines partial recipes across pages into complete recipes

### Append/Upsert Mode

```bash
# Add newly captured pages to existing catalog
python recipe_cataloger.py -f new_page.png -m claude-sonnet-4-20250514 --append-to recipe_catalog.json

# Reprocess a folder and merge into existing catalog
python recipe_cataloger.py /path/to/new_images/ -m claude-sonnet-4-20250514 --append-to recipe_catalog.json
```

### List and Delete Recipes

```bash
# Simple alphabetical list with numbers
python recipe_cataloger.py -l -c recipe_catalog.json

# Full list grouped by chapter with stats
python recipe_cataloger.py --list -c recipe_catalog.json

# Delete specific recipes by number
python recipe_cataloger.py --delete 45 67 -c recipe_catalog.json

# Delete multiple recipes at once
python recipe_cataloger.py --delete 111 112 113 114 -c recipe_catalog.json
```

Example `--list` output:
```
📚 RECIPE CATALOG SUMMARY
============================================================

📖 Chapters (5):
   • Salads: 23 recipes
   • Soups: 18 recipes
   ...

📋 All Recipes (112):
------------------------------------------------------------

   [Salads]
     1. Cold Carrot Tofu Salad (DAIRY-FREE, NUT-FREE, VEGAN)
     2. Tandoori Tofu Salad (DAIRY-FREE, GLUTEN-FREE, NUT-FREE, VEGAN)
     3. Mediterranean Quinoa Bowl
   ...

============================================================
Total: 112 recipes
Use --delete <num> [num2 ...] to remove recipes by number
============================================================
```

### All Arguments

| Argument | Description |
|----------|-------------|
| `folder` | Path to folder containing cookbook images |
| `-f, --file` | Process one or more image files (in order for multi-page recipes) |
| `-m, --model` | Vision model to use (default: llava) |
| `-o, --output` | Output JSON file path |
| `-c, --catalog` | Path to existing catalog JSON (for --random, --list, -l, --delete) |
| `-r, --retries` | Max retry attempts per image (default: 2) |
| `-l` | Simple alphabetical list of recipes with numbers |
| `--list` | List all recipes with numbers (grouped by chapter with stats) |
| `--delete` | Delete recipes by number (use --list or -l to see numbers) |
| `--append-to` | Append/upsert to existing catalog JSON (merges duplicates) |
| `--sort-by` | How to sort folder files: `name` (alphabetical, default) or `date` (oldest first) |
| `--api-key` | Anthropic API key for Claude models |
| `--backup-model` | Fallback model for files > 5MB |
| `--chapter-title` | Chapter context for file processing |
| `--debug` | Run diagnostic analysis on extraction failures |
| `--check-only` | Only verify model availability |

### Output Format

The catalog JSON includes:
- **recipes**: Array of extracted recipes with ingredients, instructions, nutrition
- **chapters**: Chapter/section information
- **processing_log**: Per-file extraction details
- **metadata**: Source folder, model used, timestamps
- **upsert_log**: History of additions, updates, and merges

### Smart Features

**Fuzzy Name Matching**: When upserting, recipes with similar names (e.g., "COCONUT MACADAMIA" vs "COCONUT MACADEMIA") are recognized as the same recipe.

**Duplicate Merging**: When a recipe spans multiple pages and gets extracted twice, the cataloger intelligently merges them (combining ingredients from one extraction with instructions from another).

**Chapter Reassignment**: Recipes extracted without chapter context are automatically assigned to the correct chapter based on chapter recipe lists.

**Photo-Heavy Page Handling**: Pages with large food photos are retried with enhanced prompts and optional image preprocessing (contrast/sharpening) to improve text extraction.

**Multi-Recipe Pages**: Supports pages with 2, 3, 4, or even 5+ short recipes - extracts all of them.

Each recipe now includes AI-classified fields:
- **meal_type**: `breakfast`, `lunch`, `dinner`, `dessert`, `snack`, or `any`
- **dish_role**: `main`, `side`, or `sub_recipe`

**Meal Type Classification:**
| Type | Examples |
|------|----------|
| breakfast | Eggs, pancakes, oatmeal, breakfast burritos |
| lunch | Sandwiches, lighter salads, soups, wraps |
| dinner | Steaks, roasts, hearty pasta, substantial proteins |
| dessert | Cakes, cookies, pies, cheesecakes, brownies |
| snack | Protein bars, shakes, smoothies, bites |
| any | Versatile dishes that work for multiple meals |

**Dish Role Classification:**
| Role | Examples |
|------|----------|
| main | Entrées, substantial dishes that are the star of a meal |
| side | Vegetables, slaws, accompaniments |
| sub_recipe | Dressings, sauces, marinades, spice blends (components) |

---

## Page Analyzer

Review extraction quality and reprocess failed pages.

### Analyze Catalog for Failures

```bash
# Review catalog for missed/failed extractions
python page_analyzer.py --analyze-catalog recipe_catalog.json

# Dry run - see what would be reprocessed
python page_analyzer.py --analyze-catalog recipe_catalog.json --dry-run -m claude-sonnet-4-20250514

# Actually reprocess failed files
python page_analyzer.py --analyze-catalog recipe_catalog.json --reprocess -m claude-sonnet-4-20250514 --backup-model qwen2-vl:8b
```

### Page Number Analysis

```bash
# Analyze page coverage (find missing pages)
python page_analyzer.py /path/to/images/ -m llava

# Correlate with recipe catalog
python page_analyzer.py /path/to/images/ -m llava -c recipe_catalog.json

# Test single image for page numbers
python page_analyzer.py -f /path/to/image.png -m qwen2-vl:8b -r 3
```

### All Arguments

| Argument | Description |
|----------|-------------|
| `folder` | Path to folder containing cookbook images |
| `-f, --file` | Test a single image file |
| `-m, --model` | Vision model to use (default: llava) |
| `-c, --catalog` | Recipe catalog JSON to correlate with |
| `-o, --output` | Output JSON file path |
| `-r, --retries` | Max retry attempts per image (default: 2) |
| `--analyze-catalog` | Analyze catalog for failed extractions |
| `--reprocess` | Reprocess failed files (use with --analyze-catalog) |
| `--dry-run` | Show what would be reprocessed without doing it |
| `--backup-model` | Backup model for large files when reprocessing |
| `--source-folder` | Override source folder for finding images |
| `--include-low-confidence` | Also reprocess low-confidence pages |
| `--cataloger-script` | Path to recipe_cataloger.py (default: recipe_cataloger.py) |
| `--api-key` | Anthropic API key for Claude (passed to recipe_cataloger for reprocessing) |
| `--check-only` | Only check if model is available |

### What Gets Flagged for Reprocessing

| Condition | Reprocessed? |
|-----------|--------------|
| Classification failed (API error) | ✅ Yes |
| "other" but has recipe indicators | ✅ Yes |
| Recipe page with 0 extractions | ✅ Yes |
| Fewer recipes than detected | ✅ Yes |
| Low confidence (with `--include-low-confidence`) | ✅ Yes |
| Legitimate non-recipe pages | ❌ No |

---

## Meal Planner

Generate random meal plans with AI-consolidated grocery lists and prep plans.

### Generate a New Meal Plan

```bash
# Generate 5 random dinner recipes (saved automatically)
python meal_planner.py -c recipe_catalog.json --meal dinner -m claude-sonnet-4-20250514 --new

# Generate 7 breakfast recipes
python meal_planner.py -c recipe_catalog.json --meal breakfast -n 7 -m claude-sonnet-4-20250514 --new

# Multiple meal types (comma-separated)
python meal_planner.py -c recipe_catalog.json --meal "lunch,dinner" -n 7 -m claude-sonnet-4-20250514 --new

# Include desserts
python meal_planner.py -c recipe_catalog.json --meal dessert -n 3 -m claude-sonnet-4-20250514 --new
```

### Multiple Catalogs

Combine recipes from multiple cookbooks:

```bash
# Select from multiple catalogs
python meal_planner.py -c cookbook1/catalog.json cookbook2/catalog.json --meal dinner -n 7 -m claude-sonnet-4-20250514 --new

# Mix and match
python meal_planner.py -c shredded/catalog.json sopranos/catalog.json salads/catalog.json --meal "lunch,dinner" -n 10 --new
```

Output:
```
📚 Loaded 122 recipes from shredded/catalog.json
📚 Loaded 87 recipes from sopranos/catalog.json
📚 Loaded 112 recipes from salads/catalog.json
📊 Total: 321 recipes from 3 catalog(s)
```

### Use Saved Meal Plan

```bash
# View saved meal plan (no catalog or model needed!)
python meal_planner.py -s

# Show specific recipe by number
python meal_planner.py -s 3

# Show specific recipe by name (partial match works)
python meal_planner.py -s "Salisbury"
python meal_planner.py -s "chicken salad"
```

### Generate Grocery List / Meal Prep

```bash
# Get grocery list for saved plan (no catalog needed!)
python meal_planner.py -m claude-sonnet-4-20250514 --grocery-list

# Get meal prep plan for saved plan
python meal_planner.py -m claude-sonnet-4-20250514 --meal-prep

# Get BOTH grocery and prep plans
python meal_planner.py -m claude-sonnet-4-20250514 --grocery-list --meal-prep
```

### Interactive Mode

```bash
python meal_planner.py -c recipe_catalog.json -m claude-sonnet-4-20250514 -i
```

**Interactive Commands:**
| Command | Description |
|---------|-------------|
| `plan <meal_type> [count]` | Generate new meal plan |
| `show` | Show current meal plan |
| `recipe <name\|number\|all>` | Show recipe details |
| `grocery` | Generate AI grocery list |
| `prep` | Generate AI meal prep plan |
| `reroll <number>` | Replace a recipe |
| `save <filename>` | Export plan to JSON |
| `quit` | Exit |

### All Arguments

| Argument | Description |
|----------|-------------|
| `-s, --show` | Show saved meal plan. Optional: recipe number or name for details |
| `-c, --catalog` | Path to one or more recipe catalog JSON files (required for --new) |
| `-m, --model` | Model for AI features (required for --new, --grocery-list, --meal-prep) |
| `--meal` | Meal type(s): breakfast, lunch, dinner, dessert, snack, any. Comma-separate for multiple: `lunch,dinner` |
| `-n, --count` | Number of recipes (default: 5) |
| `--new` | Generate new plan (requires -c and -m) |
| `--recipe` | Show recipe details ("all" to list all) - legacy, use -s instead |
| `--grocery-list` | Generate consolidated grocery list (uses saved plan if no -c) |
| `--meal-prep` | Generate meal prep plan (uses saved plan if no -c) |
| `--no-grocery` | Skip grocery list generation |
| `-i, --interactive` | Interactive mode (requires -c) |
| `--save` | Export meal plan to JSON file |
| `--api-key` | Anthropic API key for Claude |

### Meal Filtering

When selecting recipes, the planner automatically:
- **Excludes desserts and snacks** from breakfast/lunch/dinner (unless explicitly requested)
- **Excludes sub-recipes** (dressings, sauces, marinades) from all meal plans
- **Includes "any" type recipes** in lunch and dinner pools

### AI Features

**Grocery List** - Intelligently consolidates ingredients:
- Combines duplicates (3 recipes need eggs → "1 dozen eggs")
- Converts to shopping quantities ("1 bunch cilantro" not "2 tbsp")
- Groups by store section (Produce, Meat, Dairy, Pantry)
- Skips common staples

**Meal Prep Plan** - Batch prep for the week:
- Combines similar tasks (chop all onions at once)
- Groups by task type (chopping, marinating, sauce-making)
- Includes storage instructions and timing
- Suggests optimal cooking order for the week

---

## Weekly Builder (Macro-Aware Plans)

Builds a full 7-day plan against calorie and protein targets instead of random selection.
Designed around a 90-day muscle program: a graduated calorie ramp, a grazer meal structure
(three meals + three snack/shake slots), a daily protein floor, and two planning modes.

### The Calorie Ramp

| Program Week | Training Days | Rest Days |
|--------------|---------------|-----------|
| 1–2 | 2,300 kcal | 2,050 kcal |
| 3 | 2,450 kcal | 2,200 kcal |
| 4 | 2,600 kcal | 2,350 kcal |
| 5 | 2,700 kcal | 2,450 kcal |
| 6–13 | 2,800 kcal | 2,550 kcal |

Protein floor defaults to 180 g/day. Override either via the form or API.

### Modes

- **Variety (balanced cooking budget)**: ~14 distinct recipes per week — 3 rotating
  breakfasts, 4 dinner mains each cooked double so tonight's dinner becomes tomorrow's
  lunch, a Monday lunch anchor, and 2+2 rotating snacks/shakes. Snack slots enforce
  protein floors (no cookies posing as snacks), recipes with sub-recipe chains are
  deprioritized, serving multipliers stay clean (0.5 / 1 / 1.5 / 2), and recipes from
  your last two weekly plans rotate out. The plan includes a cook_plan (which dinner
  gets cooked when, and what each cook covers).
- **Simple**: one fixed staple menu repeated all week for batch cooking
  (lunch/dinner alternate between two options).
- Both modes drop the evening snack on rest days to hit the lighter target.

### Web UI

`/plans/weekly` — the Weekly Builder form (also linked from the classic generator).
Weekly plans render on the plan page as a 7-day grid with per-slot and per-day macros.
Grocery list and prep plan generation work on weekly plans exactly as before.

### API

```bash
# Generate a weekly plan
curl -X POST http://localhost:8000/api/plans/generate-weekly \
  -H "Content-Type: application/json" \
  -d '{"week_number": 1, "mode": "variety", "protein_target": 180}'

# One-time macro backfill for recipes missing nutrition data
curl -X POST http://localhost:8000/api/plans/enrich-macros \
  -H "Content-Type: application/json" \
  -d '{"use_llm": true}'
```

Macro estimation uses the configured LLM (Ollama or Claude) once per recipe and caches
results in the recipe rows; a deterministic ingredient-table estimator is the fallback
when no model is reachable (`"use_llm": false`).

### Bundled Catalogs

| File | Contents |
|------|----------|
| `data/catalogs/builder_staples.json` | 10 grazer staples (shakes, bowls, plates) with verified macros — import this or the snack slots have little to work with |
| `data/catalogs/perfect_bodybuilding_cookbook.json` | 26 recipes parsed from The Perfect Bodybuilding Cookbook (macros filled by enrichment) |

### Deploying (production checklist)

```bash
# 1. Apply the migration
mysql -u <user> -p meal_planner < database/migrations/006_weekly_plans.sql

# 2. Import the new catalogs (--enrich fills macros via the LLM at import time)
python scripts/import_catalog.py data/catalogs/builder_staples.json
python scripts/import_catalog.py data/catalogs/perfect_bodybuilding_cookbook.json --enrich

# 3. Backfill macros on EXISTING recipes (once)
curl -X POST http://localhost:8000/api/plans/enrich-macros -H "Content-Type: application/json" -d '{}'

# 4. Restart the FastAPI service
```

### Testing Without a Database

```bash
python scripts/test_weekly_planner.py
```

Runs the full pipeline (schema, catalog import, macro backfill, three plan generations
through the real API) against a throwaway SQLite database.

---

## Complete Workflow Example

### 1. Capture Cookbook Pages
Take screenshots or photos of your cookbook pages.

### 2. Extract Recipes
```bash
# Initial extraction
python recipe_cataloger.py ~/cookbook_photos/ -m claude-sonnet-4-20250514 --backup-model qwen2-vl:8b

# Output: recipe_catalog.json with 85 recipes
```

### 3. Review and Fix Failures
```bash
# Check for missed recipes
python page_analyzer.py --analyze-catalog recipe_catalog.json --dry-run -m claude-sonnet-4-20250514

# Reprocess failures
python page_analyzer.py --analyze-catalog recipe_catalog.json --reprocess -m claude-sonnet-4-20250514 --backup-model qwen2-vl:8b
```

### 4. Plan Your Week
```bash
# Generate meal plan
python meal_planner.py -c recipe_catalog.json --meal dinner -n 5 -m claude-sonnet-4-20250514 --new

# Get grocery list
python meal_planner.py -c recipe_catalog.json -m claude-sonnet-4-20250514 --grocery-list

# Get prep plan for Sunday batch cooking
python meal_planner.py -c recipe_catalog.json -m claude-sonnet-4-20250514 --meal-prep
```

### 5. During the Week
```bash
# Check tonight's recipe
python meal_planner.py -c recipe_catalog.json -m claude-sonnet-4-20250514 --recipe "cajun pork chops"
```

---

## Model Recommendations

| Use Case | Recommended Model |
|----------|-------------------|
| Best accuracy | `claude-sonnet-4-20250514` |
| Good balance | `qwen2-vl:8b` |
| Fast/free local | `llava` |
| Backup for large files | `qwen2-vl:8b` or `qwen3-vl:30b` |
| Text-only (meal planning) | `llama3.2` or `claude-sonnet-4-20250514` |

---

## Troubleshooting

### "File too large for Claude"
Use `--backup-model` to specify a fallback:
```bash
python recipe_cataloger.py -f large_image.png -m claude-sonnet-4-20250514 --backup-model qwen2-vl:8b
```

### "Cannot connect to Ollama"
```bash
# Make sure Ollama is running
ollama serve

# Check available models
ollama list
```

### "Claude API key required"
```bash
export ANTHROPIC_API_KEY="sk-ant-api03-..."
# Or use --api-key flag
```

### Missed recipes
```bash
# Run diagnostics on problematic file
python recipe_cataloger.py -f problem_page.png -m claude-sonnet-4-20250514 --debug

# Reprocess with page analyzer
python page_analyzer.py --analyze-catalog recipe_catalog.json --reprocess -m claude-sonnet-4-20250514
```

---

## File Outputs

| File | Created By | Purpose |
|------|------------|---------|
| `recipe_catalog.json` | recipe_cataloger | Main recipe database |
| `page_analysis.json` | page_analyzer | Page coverage analysis |
| `~/.meal_plan_state.json` | meal_planner | Saved meal plan state (central location) |
| `meal_plan.json` | meal_planner --save | Exported meal plan |

---

## License

MIT License - Feel free to use and modify!
