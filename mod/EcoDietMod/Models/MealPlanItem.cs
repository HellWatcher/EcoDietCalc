namespace EcoDietMod.Models;

/// <summary>
/// A single planned bite with scoring details.
/// </summary>
public sealed class MealPlanItem
{
    public string Name { get; init; } = "";
    public int Calories { get; init; }
    public float SpGain { get; init; }
    public float NewSp { get; init; }
    public bool Craving { get; init; }
    public float VarietyDeltaPp { get; init; }
    public float TastinessDeltaPp { get; init; }
    public string Source { get; init; } = "";
}
