using Eco.Core.Plugins.Interfaces;
using Eco.Gameplay.Items;
using Eco.Gameplay.Objects;
using Eco.Gameplay.Players;

namespace EcoDietMod.Tracking;

/// <summary>
/// Subscribes to Eco's GlobalFoodEatenEvent at server startup.
/// Invalidates the cached plan when a player eats food.
/// </summary>
public class EcoDietEventHandler : IModInit
{
    public static ModRegistration Register() => new()
    {
        ModName = "EcoDietMod",
    };

    public static void Initialize()
    {
        Stomach.GlobalFoodEatenEvent.Add(OnFoodEaten);
    }

    private static void OnFoodEaten(User user, FoodItem food, WorldObject? table)
    {
        PlanTracker.InvalidatePlan(user);
    }
}
