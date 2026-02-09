using System;

namespace EcoDietMod.Models;

/// <summary>
/// Immutable food record used by the planner. Equality is by name (case-insensitive).
/// Stomach/available counts are kept in separate dictionaries, not on this object.
/// </summary>
public sealed class FoodCandidate : IEquatable<FoodCandidate>
{
    public string Name { get; }
    public int Calories { get; }
    public int Carbs { get; }
    public int Protein { get; }
    public int Fat { get; }
    public int Vitamins { get; }
    public int Tastiness { get; }

    public FoodCandidate(
        string name, int calories, int carbs, int protein,
        int fat, int vitamins, int tastiness)
    {
        Name = name;
        Calories = calories;
        Carbs = carbs;
        Protein = protein;
        Fat = fat;
        Vitamins = vitamins;
        Tastiness = tastiness;
    }

    public int NutrientSum => Carbs + Protein + Fat + Vitamins;

    public float Density => NutrientSum / MathF.Max(Calories, 1f);

    public bool Equals(FoodCandidate? other)
    {
        if (other is null) return false;
        return string.Equals(Name, other.Name, StringComparison.OrdinalIgnoreCase);
    }

    public override bool Equals(object? obj) => Equals(obj as FoodCandidate);

    public override int GetHashCode() => StringComparer.OrdinalIgnoreCase.GetHashCode(Name);

    public override string ToString() => $"{Name} ({Calories} cal, {NutrientSum} nutr)";
}
