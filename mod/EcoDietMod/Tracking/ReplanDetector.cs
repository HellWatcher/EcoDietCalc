using System;
using System.Collections.Generic;
using System.Numerics;
using Eco.Gameplay.Players;
using EcoDietMod.Config;
using EcoDietMod.Models;

namespace EcoDietMod.Tracking;

/// <summary>
/// Detects whether a cached plan needs recomputation based on stomach changes,
/// calorie drain, or player movement.
/// </summary>
internal static class ReplanDetector
{
    /// <summary>
    /// Determine why (if at all) a replan is needed.
    /// </summary>
    internal static ReplanReason DetectReplanReason(
        bool isStale,
        Dictionary<string, int> stomachSnapshot,
        Dictionary<string, int> currentStomach,
        int currentRemainingCal,
        float previousRemainingCal,
        Vector3 playerPosition,
        Vector3 planPosition,
        List<MealPlanItem> remaining)
    {
        // Explicit invalidation from food eaten event
        if (isStale)
        {
            // Determine if the eaten food was in the plan or off-plan
            var diff = GetStomachDiff(stomachSnapshot, currentStomach);

            if (diff.Count == 0)
            {
                // Stale flag set but no stomach change yet — wait
                return ReplanReason.None;
            }

            // Check if all newly eaten items are in the remaining plan
            if (AllItemsInPlan(diff, remaining))
                return ReplanReason.ProgressDetected;

            return ReplanReason.OffPlanEating;
        }

        // Calorie budget changed (crafting, activity, passive drain)
        if (Math.Abs(currentRemainingCal - previousRemainingCal) > 10)
            return ReplanReason.CalorieDrain;

        // Player moved significantly — food sources may have changed
        var distanceMoved = Vector3.Distance(playerPosition, planPosition);
        if (distanceMoved > PlannerConfig.Default.PositionReplanThresholdMeters)
            return ReplanReason.PlayerMoved;

        // Stomach contents changed without invalidation (shouldn't happen, but be safe)
        if (!StomachsMatch(stomachSnapshot, currentStomach))
        {
            var diff = GetStomachDiff(stomachSnapshot, currentStomach);
            if (AllItemsInPlan(diff, remaining))
                return ReplanReason.ProgressDetected;
            return ReplanReason.OffPlanEating;
        }

        return ReplanReason.None;
    }

    /// <summary>
    /// Get foods that increased in the stomach since the snapshot.
    /// Returns food name -> count increase.
    /// </summary>
    internal static Dictionary<string, int> GetStomachDiff(
        Dictionary<string, int> snapshot,
        Dictionary<string, int> current)
    {
        var diff = new Dictionary<string, int>(StringComparer.OrdinalIgnoreCase);

        foreach (var (name, count) in current)
        {
            snapshot.TryGetValue(name, out var oldCount);
            if (count > oldCount)
                diff[name] = count - oldCount;
        }

        return diff;
    }

    /// <summary>
    /// Check if all items in the diff are present in the remaining plan.
    /// </summary>
    internal static bool AllItemsInPlan(
        Dictionary<string, int> diff,
        List<MealPlanItem> remaining)
    {
        // Count remaining plan items by name
        var planCounts = new Dictionary<string, int>(StringComparer.OrdinalIgnoreCase);
        foreach (var item in remaining)
        {
            planCounts.TryGetValue(item.Name, out var count);
            planCounts[item.Name] = count + 1;
        }

        foreach (var (name, eaten) in diff)
        {
            if (!planCounts.TryGetValue(name, out var planCount) || eaten > planCount)
                return false;
        }

        return true;
    }

    /// <summary>
    /// Remove eaten items from the remaining plan (matching by name, in order).
    /// </summary>
    internal static List<MealPlanItem> FilterEatenItems(
        Dictionary<string, int> stomachSnapshot,
        Dictionary<string, int> currentStomach,
        List<MealPlanItem> remaining)
    {
        var diff = GetStomachDiff(stomachSnapshot, currentStomach);
        var updated = new List<MealPlanItem>(remaining);

        foreach (var (name, eatenCount) in diff)
        {
            var removed = 0;
            updated.RemoveAll(item =>
            {
                if (removed >= eatenCount) return false;
                if (string.Equals(item.Name, name, StringComparison.OrdinalIgnoreCase))
                {
                    removed++;
                    return true;
                }
                return false;
            });
        }

        return updated;
    }

    internal static bool StomachsMatch(
        Dictionary<string, int> snapshot,
        Dictionary<string, int> current)
    {
        if (snapshot.Count != current.Count) return false;

        foreach (var (name, count) in snapshot)
        {
            if (!current.TryGetValue(name, out var curCount) || curCount != count)
                return false;
        }

        return true;
    }
}

internal enum ReplanReason
{
    None,
    ProgressDetected,
    OffPlanEating,
    CalorieDrain,
    PlayerMoved
}
