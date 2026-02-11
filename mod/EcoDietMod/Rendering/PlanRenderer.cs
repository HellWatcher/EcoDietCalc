using System;
using System.Collections.Generic;
using System.Linq;
using System.Text;
using EcoDietMod.Models;

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
    /// Consecutive same-name foods are grouped (e.g. "Salad x2 (900 cal) +4.44 SP").
    /// </summary>
    public static string RenderPlan(
        MealPlanResult plan,
        Dictionary<FoodCandidate, string>? sources = null,
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

        var groups = GroupItems(plan.Items);

        sb.AppendLine($"--- Meal Plan ({plan.Items.Count} bites, {plan.TotalCalories} cal) ---");
        sb.AppendLine();

        for (var i = 0; i < groups.Count; i++)
        {
            var group = groups[i];
            var countLabel = group.Count > 1 ? $" x{group.Count}" : "";
            var sign = group.TotalSpGain >= 0 ? "+" : "";
            var line = $"  {i + 1}. {group.Name}{countLabel} ({group.TotalCalories} cal) " +
                       $"{sign}{group.TotalSpGain:F2} SP -> {group.FinalSp:F2}";

            if (showTags || showSources)
            {
                var tags = BuildTags(group, sources, showSources, showTags);
                if (tags.Count > 0)
                    line += $"  [{string.Join(", ", tags)}]";
            }

            sb.AppendLine(line);
        }

        if (!compact)
        {
            sb.AppendLine();
            sb.AppendLine($"--- Summary ---");
            sb.AppendLine($"  Starting SP:  {plan.StartingSp:F2}");
            sb.AppendLine($"  Final SP:     {plan.FinalSp:F2}");
            sb.AppendLine($"  SP gained:    {FormatSigned(plan.SpGainTotal)}");
            sb.AppendLine($"  Calories:     {plan.TotalCalories} used, {plan.RemainingCalories} remaining");
            sb.AppendLine($"  Variety:      {plan.VarietyCount} qualifying foods");
            if (plan.CravingsSatisfied > 0)
                sb.AppendLine($"  Cravings:     {plan.CravingsSatisfied} satisfied");
        }

        return sb.ToString();
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
            sb.AppendLine($"  {i + 1}. {item.Name} ({item.Calories} cal) {sign}{item.SpGain:F2} SP");
        }
        return sb.ToString();
    }

    /// <summary>
    /// Group consecutive same-name items, preserving first-appearance order.
    /// </summary>
    private static List<ItemGroup> GroupItems(List<MealPlanItem> items)
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

    private static List<string> BuildTags(
        ItemGroup group,
        Dictionary<FoodCandidate, string>? sources,
        bool showSources,
        bool showTags)
    {
        var tags = new List<string>();

        if (showTags)
        {
            if (group.HasCraving) tags.Add("craving");
            if (MathF.Abs(group.TotalVarietyDeltaPp) > VarietyDeltaThreshold)
                tags.Add($"variety {FormatSigned(group.TotalVarietyDeltaPp)}pp");
            if (MathF.Abs(group.TotalTastinessDeltaPp) > TastinessDeltaThreshold)
                tags.Add($"taste {FormatSigned(group.TotalTastinessDeltaPp)}pp");
        }

        if (showSources && sources != null)
        {
            var candidate = FindCandidate(sources, group.Name);
            if (candidate != null && sources.TryGetValue(candidate, out var source))
                tags.Add(source);
        }

        return tags;
    }

    private static string FormatSigned(float value)
    {
        return value >= 0 ? $"+{value:F2}" : $"{value:F2}";
    }

    private static FoodCandidate? FindCandidate(
        Dictionary<FoodCandidate, string> sources, string name)
    {
        foreach (var kvp in sources)
        {
            if (string.Equals(kvp.Key.Name, name, StringComparison.OrdinalIgnoreCase))
                return kvp.Key;
        }
        return null;
    }

    /// <summary>
    /// Internal grouping of same-name meal plan items.
    /// </summary>
    private sealed class ItemGroup
    {
        public string Name { get; }
        public int Count { get; private set; }
        public int TotalCalories { get; private set; }
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
