-- Migration 006: Weekly macro-aware plans
-- Adds plan_type discriminator and the week_structure JSON payload
-- (day-by-day slots, servings, macros, and targets) to meal_plans.

ALTER TABLE meal_plans
    ADD COLUMN plan_type VARCHAR(20) NOT NULL DEFAULT 'classic' AFTER prep_plan,
    ADD COLUMN week_structure JSON NULL AFTER plan_type;

-- Existing rows remain 'classic'; no data backfill required.
