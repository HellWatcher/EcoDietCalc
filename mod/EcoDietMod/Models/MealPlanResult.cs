using System.Collections.Generic;

namespace EcoDietMod.Models;

/// <summary>
/// Complete meal plan with summary statistics.
/// </summary>
public sealed class MealPlanResult
{
    public List<MealPlanItem> Items { get; init; } = new();
    public float StartingSp { get; init; }
    public float FinalSp { get; init; }
    public float SpGainTotal => FinalSp - StartingSp;
    public float TotalCalories { get; init; }
    public float RemainingCalories { get; init; }
    public int VarietyCount { get; init; }
    public int CravingsSatisfied { get; init; }
}
