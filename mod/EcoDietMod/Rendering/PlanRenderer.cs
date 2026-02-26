using System;
using System.Collections.Generic;
using System.Linq;
using System.Text;
using EcoDietMod.Models;
using EcoDietMod.Tracking;

namespace EcoDietMod.Rendering;

/// <summary>
/// Formats a MealPlanResult for display in Eco chat.
/// </summary>
public static class PlanRenderer
{
    private const float VarietyDeltaThreshold = 0.01f;
    private const float TastinessDeltaThreshold = 0.01f;

    /// <summary>
    /// Render a full meal plan for chat display.
    /// When discovery contains multiple sources, items are grouped by source location
    /// sorted by distance (backpack first). Single-source plans skip the group header
    /// for backward compatibility.
    /// </summary>
    public static string RenderPlan(
        MealPlanResult plan,
        DiscoveryResult? discovery = null,
        bool showSources = true,
        bool showTags = true,
        bool compact = false)
    {
        var sb = new StringBuilder();

        if (plan.Items.Count == 0)
        {
            sb.AppendLine("No food available to plan with.");
            return sb.ToString();
        }

        sb.AppendLine($"--- Meal Plan ({plan.Items.Count} bites, {plan.TotalCalories:F0} cal) ---");
        sb.AppendLine();

        var hasMultipleSources = discovery?.HasMultipleSources ?? false;

        if (hasMultipleSources && showSources)
            RenderSourceGrouped(sb, plan, discovery!, showTags);
        else
            RenderFlat(sb, plan, discovery, showSources, showTags);

        if (!compact)
        {
            sb.AppendLine();
            sb.AppendLine($"--- Summary ---");
            sb.AppendLine($"  Starting SP:  {plan.StartingSp:F2}");
            sb.AppendLine($"  Final SP:     {plan.FinalSp:F2}");
            sb.AppendLine($"  SP gained:    {FormatSigned(plan.SpGainTotal)}");
            sb.AppendLine($"  Calories:     {plan.TotalCalories:F0} used, {plan.RemainingCalories:F0} remaining");
            sb.AppendLine($"  Variety:      {plan.VarietyCount} qualifying foods");
            if (plan.CravingsSatisfied > 0)
                sb.AppendLine($"  Cravings:     {plan.CravingsSatisfied} satisfied");
        }

        return sb.ToString();
    }

    /// <summary>
    /// Assign plan items to source groups sorted by distance (backpack first).
    /// Shared by both chat and tooltip rendering paths.
    /// </summary>
    private static List<(SourceInfo Source, List<MealPlanItem> Items)> AssignToSourceGroups(
        List<MealPlanItem> items,
        DiscoveryResult discovery)
    {
        var itemsBySource = new Dictionary<string, (SourceInfo Source, List<MealPlanItem> Items)>();

        foreach (var item in items)
        {
            var candidate = FindCandidateByName(discovery.Available, item.Name);
            var source = candidate != null ? discovery.GetClosestSource(candidate) : null;
            var sourceKey = source?.Tag ?? "[backpack]";

            if (!itemsBySource.TryGetValue(sourceKey, out var group))
            {
                group = (source ?? new SourceInfo(SourceKind.Backpack, "backpack", 0f),
                         new List<MealPlanItem>());
                itemsBySource[sourceKey] = group;
            }
            group.Items.Add(item);
        }

        return itemsBySource.Values
            .OrderBy(group => group.Source.DistanceMeters)
            .ToList();
    }

    /// <summary>
    /// Render items grouped by source, sorted by distance (backpack first).
    /// Each group gets a header line: "--- From [source tag] ---"
    /// </summary>
    private static void RenderSourceGrouped(
        StringBuilder sb,
        MealPlanResult plan,
        DiscoveryResult discovery,
        bool showTags)
    {
        var sortedGroups = AssignToSourceGroups(plan.Items, discovery);

        foreach (var (source, items) in sortedGroups)
        {
            sb.AppendLine($"--- From {source.Tag} ---");

            var groups = GroupItems(items);

            var itemIndex = 0;
            foreach (var group in groups)
            {
                itemIndex++;
                var countLabel = group.Count > 1 ? $" x{group.Count}" : "";
                var sign = group.TotalSpGain >= 0 ? "+" : "";
                var line = $"  {itemIndex}. {group.Name}{countLabel} ({group.TotalCalories:F0} cal) " +
                           $"{sign}{group.TotalSpGain:F2} SP -> {group.FinalSp:F2}";

                if (showTags)
                {
                    var tags = BuildItemTags(group);
                    if (tags.Count > 0)
                        line += $"  [{string.Join(", ", tags)}]";
                }

                sb.AppendLine(line);
            }
            sb.AppendLine();
        }
    }

    /// <summary>
    /// Render items grouped by source for the tooltip — compact format with
    /// source headers, calories, running SP total, and optional tags.
    /// </summary>
    private static void RenderSourceGroupedCompact(
        StringBuilder sb,
        List<MealPlanItem> remaining,
        DiscoveryResult discovery,
        bool showTags)
    {
        var sortedGroups = AssignToSourceGroups(remaining, discovery);
        var isFirstItem = true;

        foreach (var (source, items) in sortedGroups)
        {
            sb.AppendLine($"--- From {source.Tag} ---");

            var groups = GroupItems(items);

            foreach (var group in groups)
            {
                var marker = isFirstItem ? "→" : "·";
                isFirstItem = false;

                var countLabel = group.Count > 1 ? $" x{group.Count}" : "";
                var sign = group.TotalSpGain >= 0 ? "+" : "";
                var line = $"  {marker} {group.Name}{countLabel} ({group.TotalCalories:F0} cal) " +
                           $"{sign}{group.TotalSpGain:F2} SP → {group.FinalSp:F2}";

                if (showTags)
                {
                    var tags = BuildItemTags(group);
                    if (tags.Count > 0)
                        line += $"  [{string.Join(", ", tags)}]";
                }

                sb.AppendLine(line);
            }
        }
    }

    /// <summary>
    /// Render items in flat order (backward-compatible, single source or sources disabled).
    /// </summary>
    private static void RenderFlat(
        StringBuilder sb,
        MealPlanResult plan,
        DiscoveryResult? discovery,
        bool showSources,
        bool showTags)
    {
        var groups = GroupItems(plan.Items);

        for (var i = 0; i < groups.Count; i++)
        {
            var group = groups[i];
            var countLabel = group.Count > 1 ? $" x{group.Count}" : "";
            var sign = group.TotalSpGain >= 0 ? "+" : "";
            var line = $"  {i + 1}. {group.Name}{countLabel} ({group.TotalCalories:F0} cal) " +
                       $"{sign}{group.TotalSpGain:F2} SP -> {group.FinalSp:F2}";

            if (showTags || showSources)
            {
                var tags = BuildTags(group, discovery, showSources, showTags);
                if (tags.Count > 0)
                    line += $"  [{string.Join(", ", tags)}]";
            }

            sb.AppendLine(line);
        }
    }

    /// <summary>
    /// Render a compact suggestion (for auto-suggest after eating).
    /// </summary>
    public static string RenderCompactSuggestion(List<MealPlanItem> topItems)
    {
        var sb = new StringBuilder();
        sb.AppendLine("--- Next best bites ---");
        for (var i = 0; i < topItems.Count && i < 3; i++)
        {
            var item = topItems[i];
            var sign = item.SpGain >= 0 ? "+" : "";
            sb.AppendLine($"  {i + 1}. {item.Name} ({item.Calories:F0} cal) {sign}{item.SpGain:F2} SP");
        }
        return sb.ToString();
    }

    /// <summary>
    /// Render remaining plan items for the stomach tooltip.
    /// When discovery data is available and has multiple sources, items are grouped
    /// by source location. Otherwise falls back to a flat list with enhanced detail.
    /// </summary>
    public static string RenderRemainingPlan(
        List<MealPlanItem> remaining,
        PlanStatus status,
        float? finalSp = null,
        DiscoveryResult? discovery = null,
        bool showSources = true,
        bool showTags = true)
    {
        return status switch
        {
            PlanStatus.NoFood => "EcoDiet: No food available",
            PlanStatus.StomachFull => "EcoDiet: Stomach full",
            PlanStatus.NothingToSuggest => "EcoDiet: Nothing to suggest",
            PlanStatus.Complete => $"EcoDiet: Plan complete — {finalSp:F1} SP",
            _ => RenderRemainingItems(remaining, discovery, showSources, showTags)
        };
    }

    private static string RenderRemainingItems(
        List<MealPlanItem> remaining,
        DiscoveryResult? discovery,
        bool showSources,
        bool showTags)
    {
        var totalBites = remaining.Count;
        var totalSpGain = remaining.Sum(item => item.SpGain);

        var sb = new StringBuilder();
        sb.AppendLine($"--- EcoDiet: {totalBites} bites → {FormatSigned(totalSpGain)} SP ---");

        var hasMultipleSources = discovery?.HasMultipleSources ?? false;

        if (hasMultipleSources && showSources)
        {
            RenderSourceGroupedCompact(sb, remaining, discovery!, showTags);
        }
        else
        {
            // Flat list with calories, running SP total, and optional tags
            var groups = GroupItems(remaining);

            for (var i = 0; i < groups.Count; i++)
            {
                var group = groups[i];
                var marker = i == 0 ? "→" : "·";
                var countLabel = group.Count > 1 ? $" x{group.Count}" : "";
                var sign = group.TotalSpGain >= 0 ? "+" : "";
                var line = $"  {marker} {group.Name}{countLabel} ({group.TotalCalories:F0} cal) " +
                           $"{sign}{group.TotalSpGain:F2} SP → {group.FinalSp:F2}";

                if (showTags)
                {
                    var tags = BuildItemTags(group);
                    if (tags.Count > 0)
                        line += $"  [{string.Join(", ", tags)}]";
                }

                sb.AppendLine(line);
            }
        }

        return sb.ToString();
    }

    /// <summary>
    /// Group same-name items, preserving first-appearance order.
    /// </summary>
    internal static List<ItemGroup> GroupItems(List<MealPlanItem> items)
    {
        var groups = new List<ItemGroup>();
        var indexByName = new Dictionary<string, int>(StringComparer.OrdinalIgnoreCase);

        foreach (var item in items)
        {
            if (indexByName.TryGetValue(item.Name, out var idx))
            {
                groups[idx].Add(item);
            }
            else
            {
                var group = new ItemGroup(item.Name);
                group.Add(item);
                indexByName[item.Name] = groups.Count;
                groups.Add(group);
            }
        }

        return groups;
    }

    /// <summary>
    /// Build tags for flat rendering (includes source tag from discovery).
    /// </summary>
    private static List<string> BuildTags(
        ItemGroup group,
        DiscoveryResult? discovery,
        bool showSources,
        bool showTags)
    {
        var tags = BuildItemTags(group, showTags);

        if (showSources && discovery != null)
        {
            var candidate = FindCandidateByName(discovery.Available, group.Name);
            if (candidate != null)
            {
                var source = discovery.GetClosestSource(candidate);
                if (source != null)
                    tags.Add(source.Tag);
            }
        }

        return tags;
    }

    /// <summary>
    /// Build variety/taste/craving tags only (no source).
    /// </summary>
    private static List<string> BuildItemTags(ItemGroup group, bool showTags = true)
    {
        var tags = new List<string>();

        if (!showTags) return tags;

        if (group.HasCraving) tags.Add("craving");
        if (MathF.Abs(group.TotalVarietyDeltaPp) > VarietyDeltaThreshold)
            tags.Add($"variety {FormatSigned(group.TotalVarietyDeltaPp)}pp");
        if (MathF.Abs(group.TotalTastinessDeltaPp) > TastinessDeltaThreshold)
            tags.Add($"taste {FormatSigned(group.TotalTastinessDeltaPp)}pp");

        return tags;
    }

    private static string FormatSigned(float value)
    {
        return value >= 0 ? $"+{value:F2}" : $"{value:F2}";
    }

    /// <summary>
    /// Find a FoodCandidate by name in a dictionary keyed by FoodCandidate.
    /// </summary>
    private static FoodCandidate? FindCandidateByName<T>(
        Dictionary<FoodCandidate, T> dict, string name)
    {
        foreach (var kvp in dict)
        {
            if (string.Equals(kvp.Key.Name, name, StringComparison.OrdinalIgnoreCase))
                return kvp.Key;
        }
        return null;
    }

    /// <summary>
    /// Internal grouping of same-name meal plan items.
    /// </summary>
    internal sealed class ItemGroup
    {
        public string Name { get; }
        public int Count { get; private set; }
        public float TotalCalories { get; private set; }
        public float TotalSpGain { get; private set; }
        public float FinalSp { get; private set; }
        public bool HasCraving { get; private set; }
        public float TotalVarietyDeltaPp { get; private set; }
        public float TotalTastinessDeltaPp { get; private set; }

        public ItemGroup(string name) => Name = name;

        public void Add(MealPlanItem item)
        {
            Count++;
            TotalCalories += item.Calories;
            TotalSpGain += item.SpGain;
            FinalSp = item.NewSp; // always use the last item's NewSp
            if (item.Craving) HasCraving = true;
            TotalVarietyDeltaPp += item.VarietyDeltaPp;
            TotalTastinessDeltaPp += item.TastinessDeltaPp;
        }
    }
}
