using System;
using System.Collections.Generic;
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
    /// </summary>
    public static string RenderPlan(
        MealPlanResult plan,
        Dictionary<FoodCandidate, string>? sources = null,
        bool showSources = true)
    {
        var sb = new StringBuilder();

        sb.AppendLine($"--- Meal Plan ({plan.Items.Count} items, {plan.TotalCalories} cal) ---");
        sb.AppendLine();

        if (plan.Items.Count == 0)
        {
            sb.AppendLine("No food available to plan with.");
            return sb.ToString();
        }

        for (var i = 0; i < plan.Items.Count; i++)
        {
            var item = plan.Items[i];
            var sign = item.SpGain >= 0 ? "+" : "";
            var line = $"  {i + 1}. {item.Name} ({item.Calories} cal) " +
                       $"{sign}{item.SpGain:F2} SP -> {item.NewSp:F2}";

            // Append tags
            var tags = new List<string>();
            if (item.Craving) tags.Add("craving");
            if (MathF.Abs(item.VarietyDeltaPp) > VarietyDeltaThreshold)
                tags.Add($"variety {FormatSigned(item.VarietyDeltaPp)}pp");
            if (MathF.Abs(item.TastinessDeltaPp) > TastinessDeltaThreshold)
                tags.Add($"taste {FormatSigned(item.TastinessDeltaPp)}pp");

            if (showSources && sources != null)
            {
                var candidate = FindCandidate(sources, item.Name);
                if (candidate != null && sources.TryGetValue(candidate, out var source))
                    tags.Add(source);
            }

            if (tags.Count > 0)
                line += $"  [{string.Join(", ", tags)}]";

            sb.AppendLine(line);
        }

        sb.AppendLine();
        sb.AppendLine($"--- Summary ---");
        sb.AppendLine($"  Starting SP:  {plan.StartingSp:F2}");
        sb.AppendLine($"  Final SP:     {plan.FinalSp:F2}");
        sb.AppendLine($"  SP gained:    {FormatSigned(plan.SpGainTotal)}");
        sb.AppendLine($"  Calories:     {plan.TotalCalories} used, {plan.RemainingCalories} remaining");
        sb.AppendLine($"  Variety:      {plan.VarietyCount} qualifying foods");
        if (plan.CravingsSatisfied > 0)
            sb.AppendLine($"  Cravings:     {plan.CravingsSatisfied} satisfied");

        return sb.ToString();
    }

    /// <summary>
    /// Render a compact summary (for auto-suggest after eating).
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
}
