using System;
using System.Collections.Generic;
using System.Numerics;
using Eco.Gameplay.Components.Storage;
using Eco.Gameplay.Items;
using Eco.Gameplay.Objects;
using Eco.Gameplay.Players;
using EcoDietMod.Models;

namespace EcoDietMod.Discovery;

/// <summary>
/// Discovers food from authorized storage containers within range.
/// </summary>
public static class StorageDiscovery
{
    /// <summary>
    /// Find food in storage containers the player is authorized to access.
    /// </summary>
    public static DiscoveryResult Discover(User user, float radiusMeters, TasteBuds tasteBuds)
    {
        var available = new Dictionary<FoodCandidate, int>();
        var sources = new Dictionary<FoodCandidate, List<SourceEntry>>();

        try
        {
            var playerPosition = user.Position;

            WorldObjectManager.ForEach(worldObject =>
            {
                var storageComponent = worldObject.GetComponent<StorageComponent>();
                if (storageComponent?.Inventory == null)
                    return;

                var distance = Vector3.Distance(playerPosition, worldObject.Position);
                if (distance > radiusMeters)
                    return;

                // Check authorization
                if (!IsAuthorized(worldObject, user))
                    return;

                var displayName = worldObject.DisplayName.ToString();
                var sourceInfo = new SourceInfo(
                    SourceKind.Storage,
                    string.IsNullOrEmpty(displayName) ? worldObject.GetType().Name : displayName,
                    distance)
                { WorldObj = worldObject };

                foreach (var stack in storageComponent.Inventory.Stacks)
                {
                    if (stack.Item is not FoodItem foodItem)
                        continue;

                    var candidate = StomachSnapshot.FoodItemToCandidate(foodItem, tasteBuds);
                    if (candidate == null) continue;

                    var quantity = stack.Quantity;
                    if (quantity <= 0) continue;

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
            });
        }
        catch (Exception)
        {
            // Storage discovery is best-effort; don't crash the planner
        }

        return new DiscoveryResult { Available = available, Sources = sources };
    }

    private static bool IsAuthorized(WorldObject worldObject, User user)
    {
        try
        {
            return worldObject.Auth?.IsAuthorizedConsumerAccess(user.Player) ?? false;
        }
        catch
        {
            return false;
        }
    }
}
