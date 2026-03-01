using System.Collections.Generic;
using Eco.Gameplay.Items;
using Eco.Gameplay.Players;
using EcoDietMod.Config;
using EcoDietMod.Models;

namespace EcoDietMod.Discovery;

/// <summary>
/// Enumerates available food from various sources (backpack, storage, shops).
/// Orchestrates per-source discovery and merges results.
/// </summary>
public static class FoodDiscovery
{
    /// <summary>
    /// Discover food from the player's backpack.
    /// </summary>
    public static DiscoveryResult DiscoverFromBackpack(User user)
    {
        var available = new Dictionary<FoodCandidate, int>();
        var sources = new Dictionary<FoodCandidate, List<SourceEntry>>();
        var tasteBuds = user.Stomach.TasteBuds;
        var backpackSource = new SourceInfo(SourceKind.Backpack, "backpack", 0f);

        var inventory = user.Inventory;
        if (inventory == null)
            return new DiscoveryResult { Available = available, Sources = sources };

        foreach (var stack in inventory.Stacks)
        {
            if (stack.Item is not FoodItem foodItem)
                continue;

            var candidate = StomachSnapshot.FoodItemToCandidate(foodItem, tasteBuds);
            if (candidate == null) continue;

            var quantity = stack.Quantity;
            if (quantity <= 0) continue;

            available.TryGetValue(candidate, out var existing);
            available[candidate] = existing + quantity;

            if (!sources.TryGetValue(candidate, out var entries))
            {
                entries = new List<SourceEntry>();
                sources[candidate] = entries;
            }
            entries.Add(new SourceEntry { Source = backpackSource, Quantity = quantity });
        }

        return new DiscoveryResult { Available = available, Sources = sources };
    }

    /// <summary>
    /// Discover food from all configured sources (backpack + storage + shops).
    /// </summary>
    public static DiscoveryResult DiscoverAll(User user, DisplayConfig? displayConfig = null)
    {
        var config = new PlannerConfig();
        var tasteBuds = user.Stomach.TasteBuds;
        var results = new List<DiscoveryResult>();

        // Player-configurable radius (server default when no DisplayConfig)
        var radius = displayConfig?.MaxDiscoveryRadius ?? config.DiscoveryRadiusMeters;

        // Always include backpack
        results.Add(DiscoverFromBackpack(user));

        // Storage discovery
        if (config.EnableStorageDiscovery)
        {
            results.Add(StorageDiscovery.Discover(user, radius, tasteBuds));
        }

        // Shop discovery
        if (config.EnableShopDiscovery)
        {
            var shopFilter = new ShopFilter
            {
                CurrencyFilter = displayConfig?.ShopCurrencyFilter ?? new List<string>(),
                MaxCostPer1000Cal = displayConfig?.MaxCostPer1000Cal ?? 0f
            };
            results.Add(ShopDiscovery.Discover(user, radius, tasteBuds, shopFilter));
        }

        return results.Count == 1
            ? results[0]
            : DiscoveryMerger.Merge(results);
    }

    /// <summary>
    /// Build a complete set of FoodCandidates from the player's known foods
    /// (via TasteBuds.FoodToTaste), regardless of availability.
    /// Useful for populating the full food catalog.
    /// </summary>
    public static Dictionary<FoodCandidate, int> BuildFoodCatalog(User user)
    {
        var catalog = new Dictionary<FoodCandidate, int>();
        var tasteBuds = user.Stomach.TasteBuds;

        if (tasteBuds?.FoodToTaste == null)
            return catalog;

        foreach (var kvp in tasteBuds.FoodToTaste)
        {
            var foodType = kvp.Key;
            var foodItem = Item.Get(foodType) as FoodItem;
            if (foodItem == null) continue;

            var candidate = StomachSnapshot.FoodItemToCandidate(foodItem, tasteBuds);
            if (candidate == null) continue;

            catalog[candidate] = 0;
        }

        return catalog;
    }
}
