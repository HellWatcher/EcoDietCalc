using System;
using System.Collections.Generic;
using System.Numerics;
using Eco.Gameplay.Players;
using EcoDietMod.Algorithm;
using EcoDietMod.Config;
using EcoDietMod.Discovery;
using EcoDietMod.Models;

namespace EcoDietMod.Tracking;

/// <summary>
/// In-memory cache of active meal plans per player.
/// Detects progress (eaten items, calorie drain, player movement) and replans when state changes.
/// Thread-safe — tooltip calls may come from multiple threads.
/// </summary>
public static class PlanTracker
{
    private static readonly object Lock = new();

    private static readonly Dictionary<string, ActivePlan> Plans = new(StringComparer.OrdinalIgnoreCase);

    /// <summary>
    /// Get remaining plan items for the user, computing or replanning as needed.
    /// Returns an empty list if no food is available or stomach is full.
    /// </summary>
    public static List<MealPlanItem> GetRemainingItems(User user, out PlanStatus status, out float finalSp)
    {
        lock (Lock)
        {
            return GetRemainingItemsInternal(user, out status, out finalSp, out _);
        }
    }

    /// <summary>
    /// Get remaining plan items plus the DiscoveryResult for source-grouped rendering.
    /// Use this from tooltip/rendering code that needs source information.
    /// </summary>
    public static List<MealPlanItem> GetRemainingPlanContext(
        User user, out PlanStatus status, out float finalSp, out DiscoveryResult? discovery)
    {
        lock (Lock)
        {
            return GetRemainingItemsInternal(user, out status, out finalSp, out discovery);
        }
    }

    private static List<MealPlanItem> GetRemainingItemsInternal(
        User user, out PlanStatus status, out float finalSp, out DiscoveryResult? discovery)
    {
        var userName = user.Name;
        var currentStomach = CaptureStomachByName(user);
        var remainingCal = StomachSnapshot.GetRemainingCalories(user);

        if (Plans.TryGetValue(userName, out var active))
        {
            // Check if replan is needed
            var replanReason = DetectReplanReason(active, user, currentStomach, remainingCal);

            if (replanReason == ReplanReason.None)
            {
                // No changes — return cached remaining items
                finalSp = active.Result.FinalSp;
                discovery = active.Discovery;
                status = active.Remaining.Count > 0 ? PlanStatus.Active : PlanStatus.Complete;
                return active.Remaining;
            }

            if (replanReason == ReplanReason.ProgressDetected)
            {
                // Items were eaten that match the plan — filter them out
                var updated = FilterEatenItems(active, currentStomach);
                active.StomachSnapshotByName = currentStomach;
                active.RemainingCaloriesAtPlanTime = remainingCal;
                active.Remaining = updated;
                active.IsStale = false;
                finalSp = active.Result.FinalSp;
                discovery = active.Discovery;

                if (updated.Count > 0)
                {
                    status = PlanStatus.Active;
                    return updated;
                }

                // All items eaten — plan complete
                status = PlanStatus.Complete;
                return updated;
            }

            // Off-plan eating, calorie change, or player moved — full replan
        }

        // Compute fresh plan
        return ComputeFreshPlan(user, userName, currentStomach, remainingCal, out status, out finalSp, out discovery);
    }

    /// <summary>
    /// Mark a user's plan as stale (called when food is eaten).
    /// The next tooltip render will detect the change and replan if needed.
    /// </summary>
    public static void InvalidatePlan(User user)
    {
        lock (Lock)
        {
            if (Plans.TryGetValue(user.Name, out var active))
                active.IsStale = true;
        }
    }

    /// <summary>
    /// Remove the user's cached plan entirely.
    /// Next tooltip render will compute a fresh plan from scratch.
    /// Use for config changes or other non-stomach triggers.
    /// </summary>
    public static void ClearPlan(User user)
    {
        lock (Lock)
        {
            Plans.Remove(user.Name);
        }
    }

    private static List<MealPlanItem> ComputeFreshPlan(
        User user, string userName,
        Dictionary<string, int> currentStomach,
        int remainingCal,
        out PlanStatus status,
        out float finalSp,
        out DiscoveryResult? discovery)
    {
        finalSp = 0f;

        var displayConfig = DisplayConfig.Load(userName);
        discovery = FoodDiscovery.DiscoverAll(user, displayConfig);
        if (discovery.Available.Count == 0)
        {
            Plans.Remove(userName);
            discovery = null;
            status = PlanStatus.NoFood;
            return new List<MealPlanItem>();
        }

        if (remainingCal <= 0)
        {
            Plans.Remove(userName);
            status = PlanStatus.StomachFull;
            return new List<MealPlanItem>();
        }

        var stomachState = StomachSnapshot.CaptureStomach(user);
        var cravings = BuildCravingsList(user);
        var cravingsSatisfied = StomachSnapshot.GetCravingsSatisfied(user);
        var dinnerPartyMult = StomachSnapshot.GetDinnerPartyMult(user);
        var config = new PlannerConfig();

        var result = MealPlanner.PlanMeal(
            stomachState, discovery.Available, cravings, cravingsSatisfied,
            remainingCal, config, dinnerPartyMult: dinnerPartyMult);

        finalSp = result.FinalSp;

        if (result.Items.Count == 0)
        {
            Plans.Remove(userName);
            status = PlanStatus.NothingToSuggest;
            return new List<MealPlanItem>();
        }

        var activePlan = new ActivePlan
        {
            Result = result,
            Discovery = discovery,
            StomachSnapshotByName = currentStomach,
            RemainingCaloriesAtPlanTime = remainingCal,
            PlayerPositionAtPlanTime = user.Position,
            ComputedAt = DateTime.UtcNow,
            Remaining = new List<MealPlanItem>(result.Items),
            IsStale = false
        };

        Plans[userName] = activePlan;
        status = PlanStatus.Active;
        return activePlan.Remaining;
    }

    private static ReplanReason DetectReplanReason(
        ActivePlan active,
        User user,
        Dictionary<string, int> currentStomach,
        int currentRemainingCal)
    {
        // Explicit invalidation from food eaten event
        if (active.IsStale)
        {
            // Determine if the eaten food was in the plan or off-plan
            var diff = GetStomachDiff(active.StomachSnapshotByName, currentStomach);

            if (diff.Count == 0)
            {
                // Stale flag set but no stomach change yet — wait
                return ReplanReason.None;
            }

            // Check if all newly eaten items are in the remaining plan
            if (AllItemsInPlan(diff, active.Remaining))
                return ReplanReason.ProgressDetected;

            return ReplanReason.OffPlanEating;
        }

        // Calorie budget changed (crafting, activity, passive drain)
        if (Math.Abs(currentRemainingCal - active.RemainingCaloriesAtPlanTime) > 10)
            return ReplanReason.CalorieDrain;

        // Player moved significantly — food sources may have changed
        var config = new PlannerConfig();
        var distanceMoved = Vector3.Distance(user.Position, active.PlayerPositionAtPlanTime);
        if (distanceMoved > config.PositionReplanThresholdMeters)
            return ReplanReason.PlayerMoved;

        // Stomach contents changed without invalidation (shouldn't happen, but be safe)
        if (!StomachsMatch(active.StomachSnapshotByName, currentStomach))
        {
            var diff = GetStomachDiff(active.StomachSnapshotByName, currentStomach);
            if (AllItemsInPlan(diff, active.Remaining))
                return ReplanReason.ProgressDetected;
            return ReplanReason.OffPlanEating;
        }

        return ReplanReason.None;
    }

    /// <summary>
    /// Get foods that increased in the stomach since the snapshot.
    /// Returns food name -> count increase.
    /// </summary>
    private static Dictionary<string, int> GetStomachDiff(
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
    private static bool AllItemsInPlan(
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
    private static List<MealPlanItem> FilterEatenItems(
        ActivePlan active,
        Dictionary<string, int> currentStomach)
    {
        var diff = GetStomachDiff(active.StomachSnapshotByName, currentStomach);
        var remaining = new List<MealPlanItem>(active.Remaining);

        foreach (var (name, eatenCount) in diff)
        {
            var removed = 0;
            remaining.RemoveAll(item =>
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

        return remaining;
    }

    private static bool StomachsMatch(
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

    /// <summary>
    /// Capture stomach as a simple name -> count dictionary for comparison.
    /// </summary>
    private static Dictionary<string, int> CaptureStomachByName(User user)
    {
        var stomach = StomachSnapshot.CaptureStomach(user);
        var byName = new Dictionary<string, int>(StringComparer.OrdinalIgnoreCase);

        foreach (var (candidate, count) in stomach)
            byName[candidate.Name] = count;

        return byName;
    }

    private static List<string> BuildCravingsList(User user)
    {
        var cravings = new List<string>();
        var currentCraving = StomachSnapshot.GetCurrentCraving(user);
        if (currentCraving != null)
            cravings.Add(currentCraving);
        return cravings;
    }

    private sealed class ActivePlan
    {
        public MealPlanResult Result { get; init; } = null!;
        public DiscoveryResult Discovery { get; init; } = null!;
        public Dictionary<string, int> StomachSnapshotByName { get; set; } = new();
        public float RemainingCaloriesAtPlanTime { get; set; }
        public Vector3 PlayerPositionAtPlanTime { get; set; }
        public DateTime ComputedAt { get; set; }
        public List<MealPlanItem> Remaining { get; set; } = new();
        public bool IsStale { get; set; }
    }

    private enum ReplanReason
    {
        None,
        ProgressDetected,
        OffPlanEating,
        CalorieDrain,
        PlayerMoved
    }
}

/// <summary>
/// Status of the plan for rendering edge cases.
/// </summary>
public enum PlanStatus
{
    Active,
    Complete,
    NoFood,
    StomachFull,
    NothingToSuggest
}
