using System;
using System.Collections.Generic;
using Eco.Gameplay.Items;
using Eco.Gameplay.Players;
using EcoDietMod.Models;

namespace EcoDietMod.Discovery;

/// <summary>
/// Enumerates available food from various sources (backpack, storage, shops).
/// Phase 2 implements backpack only; Phase 3 adds storage and shops.
/// </summary>
public static class FoodDiscovery
{
    /// <summary>
    /// Discover all available food and their quantities from the player's backpack.
    /// Each food is tagged with its source for display purposes.
    /// </summary>
    public static (Dictionary<FoodCandidate, int> Available, Dictionary<FoodCandidate, string> Sources)
        DiscoverFromBackpack(User user)
    {
        var available = new Dictionary<FoodCandidate, int>();
        var sources = new Dictionary<FoodCandidate, string>();
        var tasteBuds = user.Stomach.TasteBuds;

        var inventory = user.Inventory;
        if (inventory == null)
            return (available, sources);

        // Iterate all items in the player's carried inventory
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

            if (!sources.ContainsKey(candidate))
                sources[candidate] = "[backpack]";
        }

        return (available, sources);
    }

    /// <summary>
    /// Discover food from all configured sources.
    /// Currently only backpack (Phase 2). Phase 3 will add storage and shops.
    /// </summary>
    public static (Dictionary<FoodCandidate, int> Available, Dictionary<FoodCandidate, string> Sources)
        DiscoverAll(User user)
    {
        // Phase 2: backpack only
        return DiscoverFromBackpack(user);
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

            // Catalog entry with 0 availability (actual availability comes from discovery)
            catalog[candidate] = 0;
        }

        return catalog;
    }
}
