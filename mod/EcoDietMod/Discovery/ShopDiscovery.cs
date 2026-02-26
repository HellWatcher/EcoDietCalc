using System;
using System.Collections.Generic;
using System.Linq;
using System.Numerics;
using Eco.Gameplay.Components;
using Eco.Gameplay.Components.Store;
using Eco.Gameplay.Items;
using Eco.Gameplay.Objects;
using Eco.Gameplay.Players;
using EcoDietMod.Models;

namespace EcoDietMod.Discovery;

/// <summary>
/// Filter criteria for shop food discovery.
/// </summary>
public sealed class ShopFilter
{
    /// <summary>Only accept these currencies (empty = accept all).</summary>
    public List<string> CurrencyFilter { get; init; } = new();

    /// <summary>Max cost per 1000 calories (0 = no limit).</summary>
    public float MaxCostPer1000Cal { get; init; }
}

/// <summary>
/// Discovers food available for purchase from nearby shops.
/// </summary>
public static class ShopDiscovery
{
    /// <summary>
    /// Find food sold at nearby shops, filtered by distance, currency, and cost efficiency.
    /// </summary>
    public static DiscoveryResult Discover(
        User user, float radiusMeters, TasteBuds tasteBuds, ShopFilter filter)
    {
        var available = new Dictionary<FoodCandidate, int>();
        var sources = new Dictionary<FoodCandidate, List<SourceEntry>>();

        try
        {
            var playerPosition = user.Position;

            WorldObjectManager.ForEach(worldObject =>
            {
                var store = worldObject.GetComponent<StoreComponent>();
                if (store == null)
                    return;

                var distance = Vector3.Distance(playerPosition, worldObject.Position);
                if (distance > radiusMeters)
                    return;

                var ownerName = worldObject.Owners?.Name ?? "Shop";
                var currencyName = store.CurrencyName;

                ProcessStoreOffers(
                    store, ownerName, currencyName, distance, tasteBuds, filter,
                    available, sources);
            });
        }
        catch (Exception)
        {
            // Shop discovery is best-effort; don't crash the planner
        }

        return new DiscoveryResult { Available = available, Sources = sources };
    }

    private static void ProcessStoreOffers(
        StoreComponent store,
        string ownerName,
        string currencyName,
        float distance,
        TasteBuds tasteBuds,
        ShopFilter filter,
        Dictionary<FoodCandidate, int> available,
        Dictionary<FoodCandidate, List<SourceEntry>> sources)
    {
        try
        {
            // Apply currency filter at store level (all offers share the same currency)
            if (filter.CurrencyFilter.Count > 0)
            {
                var currency = currencyName ?? "";
                if (!filter.CurrencyFilter.Any(
                    allowed => string.Equals(allowed, currency, StringComparison.OrdinalIgnoreCase)))
                    return;
            }

            foreach (var offer in store.AllOffers)
            {
                // Only sell offers (shop selling to player)
                if (!offer.Buying)
                    continue;

                // Must be a food item
                if (offer.Stack?.Item is not FoodItem foodItem)
                    continue;

                // Apply cost efficiency filter
                var pricePerUnit = offer.Price;
                if (filter.MaxCostPer1000Cal > 0 && foodItem.Calories > 0)
                {
                    var costPer1000Cal = pricePerUnit / foodItem.Calories * 1000f;
                    if (costPer1000Cal > filter.MaxCostPer1000Cal)
                        continue;
                }

                var candidate = StomachSnapshot.FoodItemToCandidate(foodItem, tasteBuds);
                if (candidate == null) continue;

                var quantity = offer.Stack.Quantity;
                if (quantity <= 0) continue;

                var sourceInfo = new SourceInfo(SourceKind.Shop, ownerName, distance)
                {
                    PricePerUnit = pricePerUnit,
                    Currency = currencyName
                };

                // Sum availability
                available.TryGetValue(candidate, out var existing);
                available[candidate] = existing + quantity;

                // Track source
                if (!sources.TryGetValue(candidate, out var entries))
                {
                    entries = new List<SourceEntry>();
                    sources[candidate] = entries;
                }
                entries.Add(new SourceEntry { Source = sourceInfo, Quantity = quantity });
            }
        }
        catch (Exception)
        {
            // Individual store errors shouldn't halt discovery
        }
    }
}
