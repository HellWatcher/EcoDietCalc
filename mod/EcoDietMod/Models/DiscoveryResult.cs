using System.Collections.Generic;
using System.Linq;

namespace EcoDietMod.Models;

/// <summary>
/// A single source contribution for a food item (source + quantity available there).
/// </summary>
public sealed class SourceEntry
{
    public SourceInfo Source { get; init; } = null!;
    public int Quantity { get; init; }
}

/// <summary>
/// Combined result of food discovery across all sources.
/// Tracks total availability per food and per-source breakdown.
/// </summary>
public sealed class DiscoveryResult
{
    /// <summary>Total available quantity per food (summed across all sources).</summary>
    public Dictionary<FoodCandidate, int> Available { get; init; } = new();

    /// <summary>Per-food list of source entries (where each unit came from).</summary>
    public Dictionary<FoodCandidate, List<SourceEntry>> Sources { get; init; } = new();

    /// <summary>
    /// Get the closest source for a food item, or null if not found.
    /// </summary>
    public SourceInfo? GetClosestSource(FoodCandidate food) =>
        Sources.TryGetValue(food, out var entries)
            ? entries.MinBy(entry => entry.Source.DistanceMeters)?.Source
            : null;

    /// <summary>
    /// Whether this result contains food from multiple distinct source kinds.
    /// Used to decide whether to show source group headers in rendering.
    /// </summary>
    public bool HasMultipleSources =>
        Sources.Values
            .SelectMany(entries => entries)
            .Select(entry => entry.Source)
            .DistinctBy(source => (source.Kind, source.Label))
            .Count() > 1;
}
