using System;
using System.Collections.Generic;
using System.Linq;
using EcoDietMod.Models;

namespace EcoDietMod.Rendering;

/// <summary>
/// Shared utilities for grouping and formatting meal plan items.
/// </summary>
public static class ItemGrouping
{
    /// <summary>
    /// Group same-name items, preserving first-appearance order.
    /// </summary>
    public static List<ItemGroup> GroupItems(List<MealPlanItem> items)
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
    /// Assign plan items to source groups sorted by distance (backpack first).
    /// </summary>
    public static List<(SourceInfo Source, List<MealPlanItem> Items)> AssignToSourceGroups(
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
    /// Find a FoodCandidate by name in a dictionary keyed by FoodCandidate.
    /// </summary>
    public static FoodCandidate? FindCandidateByName<T>(
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
    /// Format a float value with explicit sign prefix.
    /// </summary>
    public static string FormatSigned(float value)
    {
        return value >= 0 ? $"+{value:F2}" : $"{value:F2}";
    }
}
