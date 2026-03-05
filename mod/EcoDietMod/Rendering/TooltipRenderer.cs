using System;
using System.Collections.Generic;
using System.Linq;
using Eco.Gameplay.Items;
using Eco.Gameplay.Systems.TextLinks;
using Eco.Shared.Localization;
using Eco.Shared.Logging;
using Eco.Shared.Utils;
using EcoDietMod.Models;

namespace EcoDietMod.Rendering;

using RT = RichText;

/// <summary>
/// Renders meal plan data for the stomach tooltip using native UILinks.
/// Food names and source names become interactive hover/click links.
/// </summary>
public static class TooltipRenderer
{
    private const float VarietyDeltaThreshold = 0.01f;
    private const float TastinessDeltaThreshold = 0.01f;

    /// <summary>
    /// Render remaining plan items for the stomach tooltip using native UILinks.
    /// </summary>
    public static LocString RenderRemainingPlanTooltip(
        List<MealPlanItem> remaining,
        PlanStatus status,
        float? finalSp = null,
        DiscoveryResult? discovery = null,
        bool showSources = true,
        bool showTags = true,
        bool compact = false)
    {
        return status switch
        {
            PlanStatus.NoFood           => Localizer.NotLocalizedStr(
                RT.Size(Text.Subtext("EcoDiet: No food available"), RT.TooltipSize)),
            PlanStatus.StomachFull      => Localizer.NotLocalizedStr(
                RT.Size(Text.Subtext("EcoDiet: Stomach full"), RT.TooltipSize)),
            PlanStatus.NothingToSuggest => Localizer.NotLocalizedStr(
                RT.Size(Text.Subtext("EcoDiet: Nothing to suggest"), RT.TooltipSize)),
            PlanStatus.Complete         => Localizer.NotLocalizedStr(
                RT.Size(Text.Positive($"EcoDiet: Plan complete — {finalSp:F1} SP"), RT.TooltipSize)),
            _ => RenderRemainingItemsTooltip(remaining, discovery, showSources, showTags, compact)
        };
    }

    private static LocString RenderRemainingItemsTooltip(
        List<MealPlanItem> remaining,
        DiscoveryResult? discovery,
        bool showSources,
        bool showTags,
        bool compact)
    {
        var totalBites = remaining.Count;
        var totalSpGain = remaining.Sum(item => item.SpGain);
        var lsb = new LocStringBuilder();

        var spColor = totalSpGain >= 0 ? RT.SpPositive : RT.SpNegative;
        var headerText = $"--- EcoDiet: {totalBites} bites → " +
                         $"{RT.Color(ItemGrouping.FormatSigned(totalSpGain) + " SP", spColor)} ---";
        lsb.AppendLineNTStr(RT.Size(RT.Bold(RT.Color(headerText, RT.Header)), RT.TooltipSize));
        lsb.AppendLineNTStr("");

        var hasMultipleSources = discovery?.HasMultipleSources ?? false;

        if (hasMultipleSources && showSources)
            RenderSourceGroupedTooltip(lsb, remaining, discovery!, showTags, compact);
        else
            RenderFlatTooltip(lsb, remaining, discovery, showTags, compact);

        return lsb.ToLocString();
    }

    private static void RenderSourceGroupedTooltip(
        LocStringBuilder lsb,
        List<MealPlanItem> remaining,
        DiscoveryResult discovery,
        bool showTags,
        bool compact)
    {
        var sortedGroups = ItemGrouping.AssignToSourceGroups(remaining, discovery);
        var isFirstItem = true;
        var isFirstGroup = true;

        foreach (var (source, items) in sortedGroups)
        {
            if (!isFirstGroup) lsb.AppendLineNTStr("");
            isFirstGroup = false;

            // Source header: UILink for world objects, fallback to colored tag
            var sourceHeader = ResolveSourceLink(source);
            lsb.Append(Localizer.NotLocalizedStr(RT.Size(RT.Bold("--- From "), RT.TooltipSize)));
            lsb.Append(sourceHeader);
            lsb.AppendLineNTStr(RT.Size(RT.Bold(" ---"), RT.TooltipSize));

            var groups = ItemGrouping.GroupItems(items);

            foreach (var group in groups)
            {
                var line = FormatItemLineTooltip(group, discovery, isFirstItem, showTags, compact);
                lsb.AppendLine(line);
                isFirstItem = false;
            }
        }
    }

    private static void RenderFlatTooltip(
        LocStringBuilder lsb,
        List<MealPlanItem> remaining,
        DiscoveryResult? discovery,
        bool showTags,
        bool compact)
    {
        var groups = ItemGrouping.GroupItems(remaining);

        for (var i = 0; i < groups.Count; i++)
        {
            var line = FormatItemLineTooltip(groups[i], discovery, i == 0, showTags, compact);
            lsb.AppendLine(line);
        }
    }

    /// <summary>
    /// Format a single item group line for the UILink tooltip.
    /// Uses food UILinks when FoodType is available, falls back to bold text.
    /// </summary>
    private static LocString FormatItemLineTooltip(
        ItemGroup group,
        DiscoveryResult? discovery,
        bool isFirst,
        bool showTags,
        bool compact)
    {
        var lineLsb = new LocStringBuilder();
        var marker = isFirst
            ? RT.Color("→", RT.Marker)
            : RT.Color("·", RT.MarkerDot);

        var countLabel = group.Count > 1 ? $" x{group.Count}" : "";
        var foodLink = ResolveFoodLink(group.Name, discovery);
        var calLabel = RT.Color($"({group.TotalCalories:F0} cal)", RT.Calories);

        lineLsb.Append(Localizer.NotLocalizedStr(RT.Size($"  {marker} ", RT.TooltipSize)));
        lineLsb.Append(foodLink);
        lineLsb.Append(Localizer.NotLocalizedStr(RT.Size(countLabel + " ", RT.TooltipSize)));
        lineLsb.Append(Localizer.NotLocalizedStr(RT.Size(calLabel, RT.TooltipSize)));

        if (!compact)
        {
            var gainColor = group.TotalSpGain >= 0 ? RT.SpPositive : RT.SpNegative;
            var sign = group.TotalSpGain >= 0 ? "+" : "";
            var spLabel = RT.Color($"{sign}{group.TotalSpGain:F2} SP", gainColor);
            var runningLabel = RT.Color($"→ {group.FinalSp:F2}", RT.SpRunning);
            lineLsb.Append(Localizer.NotLocalizedStr(RT.Size($" {spLabel} {runningLabel}", RT.TooltipSize)));

            if (showTags)
            {
                var tags = BuildTooltipItemTags(group);
                if (tags.Count > 0)
                    lineLsb.Append(Localizer.NotLocalizedStr(
                        RT.Size($"  [{string.Join(", ", tags)}]", RT.TooltipSize)));
            }
        }

        return lineLsb.ToLocString();
    }

    /// <summary>
    /// Build colored tags for UILink tooltip rendering.
    /// Uses Text.Color (Eco's native styling) for consistency with UILinks.
    /// </summary>
    private static List<string> BuildTooltipItemTags(ItemGroup group)
    {
        var tags = new List<string>();

        if (group.HasCraving)
            tags.Add(Text.Color(RT.TagCraving, "craving"));
        if (MathF.Abs(group.TotalVarietyDeltaPp) > VarietyDeltaThreshold)
            tags.Add(Text.Color(RT.TagVariety,
                $"variety {ItemGrouping.FormatSigned(group.TotalVarietyDeltaPp)}pp"));
        if (MathF.Abs(group.TotalTastinessDeltaPp) > TastinessDeltaThreshold)
            tags.Add(Text.Color(RT.TagTaste,
                $"taste {ItemGrouping.FormatSigned(group.TotalTastinessDeltaPp)}pp"));

        return tags;
    }

    /// <summary>
    /// Resolve a source to a UILink (WorldObject) or fallback to colored tag string.
    /// </summary>
    internal static LocString ResolveSourceLink(SourceInfo source)
    {
        if (source.WorldObj != null)
        {
            try
            {
                return source.WorldObj.UILink();
            }
            catch (Exception ex)
            {
                Log.WriteWarningLineLocStr($"[EcoDiet] Source UILink failed for '{source.Label}': {ex.Message}");
            }
        }

        // Fallback: colored tag wrapped as not-localized string
        return Localizer.NotLocalizedStr(RT.Size(source.ColoredTag, RT.TooltipSize));
    }

    /// <summary>
    /// Resolve a food name to a UILink or fallback to bold text.
    /// Looks up FoodCandidate by name in discovery, then uses FoodType to get the Item.
    /// </summary>
    internal static LocString ResolveFoodLink(string name, DiscoveryResult? discovery)
    {
        if (discovery != null)
        {
            var candidate = ItemGrouping.FindCandidateByName(discovery.Available, name);
            if (candidate?.FoodType != null)
            {
                try
                {
                    var foodItem = Item.Get(candidate.FoodType) as FoodItem;
                    if (foodItem != null)
                        return foodItem.UILink();
                }
                catch (Exception ex)
                {
                    Log.WriteWarningLineLocStr($"[EcoDiet] Food UILink failed for '{name}': {ex.Message}");
                }
            }
        }

        return Localizer.NotLocalizedStr(RT.Size(RT.Bold(name), RT.TooltipSize));
    }
}
