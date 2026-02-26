using System.Collections.Generic;
using EcoDietMod.Models;

namespace EcoDietMod.Discovery;

/// <summary>
/// Merges multiple DiscoveryResults into one, summing quantities
/// and concatenating source entries per food.
/// </summary>
public static class DiscoveryMerger
{
    /// <summary>
    /// Merge discovery results from multiple sources.
    /// FoodCandidate equality is by name, so same food from different sources sums.
    /// </summary>
    public static DiscoveryResult Merge(List<DiscoveryResult> results)
    {
        var available = new Dictionary<FoodCandidate, int>();
        var sources = new Dictionary<FoodCandidate, List<SourceEntry>>();

        foreach (var result in results)
        {
            // Merge availability counts
            foreach (var (candidate, quantity) in result.Available)
            {
                available.TryGetValue(candidate, out var existing);
                available[candidate] = existing + quantity;
            }

            // Merge source entries
            foreach (var (candidate, entries) in result.Sources)
            {
                if (!sources.TryGetValue(candidate, out var merged))
                {
                    merged = new List<SourceEntry>();
                    sources[candidate] = merged;
                }
                merged.AddRange(entries);
            }
        }

        return new DiscoveryResult { Available = available, Sources = sources };
    }
}
