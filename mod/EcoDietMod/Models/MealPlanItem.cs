namespace EcoDietMod.Models;

/// <summary>
/// A single planned bite with scoring details.
/// </summary>
public sealed record MealPlanItem(
    string Name,
    float Calories,
    float SpGain,
    float NewSp,
    bool Craving,
    float VarietyDeltaPp,
    float TastinessDeltaPp);
