<?php

declare(strict_types=1);

/**
 * Helper functions for the Meal Planner application
 */

/**
 * Escape HTML entities
 */
function e(string $value): string
{
    return htmlspecialchars($value, ENT_QUOTES, 'UTF-8');
}

/**
 * Format a time string (e.g., "30 minutes")
 */
function formatTime(?string $time): string
{
    return $time ?: '-';
}

/**
 * Format meal type for display
 */
function formatMealType(string $type): string
{
    return ucfirst($type);
}

/**
 * Get badge class for meal type
 */
function mealTypeBadgeClass(string $type): string
{
    return match ($type) {
        'breakfast' => 'bg-warning text-dark',
        'lunch' => 'bg-info text-dark',
        'dinner' => 'bg-primary',
        'dessert' => 'bg-danger',
        'snack' => 'bg-secondary',
        default => 'bg-light text-dark',
    };
}

/**
 * Get badge class for dietary info
 */
function dietaryBadgeClass(string $tag): string
{
    return match (strtoupper($tag)) {
        'VEGAN' => 'bg-success',
        'VEGETARIAN' => 'bg-success',
        'GLUTEN-FREE' => 'bg-warning text-dark',
        'DAIRY-FREE' => 'bg-info text-dark',
        'NUT-FREE' => 'bg-secondary',
        default => 'bg-light text-dark',
    };
}

/**
 * Truncate text to a maximum length
 */
function truncate(string $text, int $length = 100, string $suffix = '...'): string
{
    if (mb_strlen($text) <= $length) {
        return $text;
    }
    return mb_substr($text, 0, $length) . $suffix;
}

/**
 * Format JSON array for display
 */
function formatList(?array $items): string
{
    if (empty($items)) {
        return '-';
    }
    return implode(', ', $items);
}
