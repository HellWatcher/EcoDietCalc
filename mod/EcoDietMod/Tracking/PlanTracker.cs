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

    private static List<MealPlanItem> GetRemainingItemsInternal(
        User user, out PlanStatus status, out float finalSp, out DiscoveryResult? discovery)
    {
        var userName = user.Name;
        var currentStomach = CaptureStomachByName(user);
        var remainingCal = StomachSnapshot.GetRemainingCalories(user);

        if (Plans.TryGetValue(userName, out var active))
        {
            var replanReason = ReplanDetector.DetectReplanReason(
                active.IsStale, active.StomachSnapshotByName, currentStomach,
                remainingCal, active.RemainingCaloriesAtPlanTime,
                user.Position, active.PlayerPositionAtPlanTime,
                active.Remaining);

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
                var updated = ReplanDetector.FilterEatenItems(
                    active.StomachSnapshotByName, currentStomach, active.Remaining);
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

        Dictionary<FoodCandidate, int> stomachState;
        float calorieBudget;
        int cravingsSatisfied;

        if (displayConfig.FullPlan)
        {
            stomachState = new Dictionary<FoodCandidate, int>();
            calorieBudget = StomachSnapshot.GetMaxCalories(user);
            cravingsSatisfied = 0;
        }
        else
        {
            stomachState = StomachSnapshot.CaptureStomach(user);
            calorieBudget = remainingCal;
            cravingsSatisfied = StomachSnapshot.GetCravingsSatisfied(user);
        }

        var cravings = BuildCravingsList(user);
        var dinnerPartyMult = StomachSnapshot.GetDinnerPartyMult(user);

        var result = MealPlanner.PlanMeal(
            stomachState, discovery.Available, cravings, cravingsSatisfied,
            calorieBudget, PlannerConfig.Default, dinnerPartyMult: dinnerPartyMult);

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
}
