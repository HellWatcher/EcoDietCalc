using System;

namespace EcoDietMod.Models;

/// <summary>
/// Immutable food record used by the planner. Equality is by name (case-insensitive).
/// Stomach/available counts are kept in separate dictionaries, not on this object.
/// Uses float for nutrients and calories to match Eco API precision.
/// </summary>
public sealed class FoodCandidate : IEquatable<FoodCandidate>
{
    public string Name { get; }
    public float Calories { get; }
    public float Carbs { get; }
    public float Protein { get; }
    public float Fat { get; }
    public float Vitamins { get; }
    public int Tastiness { get; }

    public FoodCandidate(
        string name, float calories, float carbs, float protein,
        float fat, float vitamins, int tastiness)
    {
        Name = name;
        Calories = calories;
        Carbs = carbs;
        Protein = protein;
        Fat = fat;
        Vitamins = vitamins;
        Tastiness = tastiness;
    }

    public float NutrientSum => Carbs + Protein + Fat + Vitamins;

    public float Density => NutrientSum / MathF.Max(Calories, 1f);

    public bool Equals(FoodCandidate? other)
    {
        if (other is null) return false;
        return string.Equals(Name, other.Name, StringComparison.OrdinalIgnoreCase);
    }

    public override bool Equals(object? obj) => Equals(obj as FoodCandidate);

    public override int GetHashCode() => StringComparer.OrdinalIgnoreCase.GetHashCode(Name);

    public override string ToString() => $"{Name} ({Calories:F0} cal, {NutrientSum:F1} nutr)";
}
