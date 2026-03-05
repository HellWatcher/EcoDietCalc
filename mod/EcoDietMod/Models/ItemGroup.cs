namespace EcoDietMod.Models;

/// <summary>
/// Groups same-name meal plan items with aggregated stats for rendering.
/// </summary>
public sealed class ItemGroup
{
    public string Name { get; }
    public int Count { get; private set; }
    public float TotalCalories { get; private set; }
    public float TotalSpGain { get; private set; }
    public float FinalSp { get; private set; }
    public bool HasCraving { get; private set; }
    public float TotalVarietyDeltaPp { get; private set; }
    public float TotalTastinessDeltaPp { get; private set; }

    public ItemGroup(string name) => Name = name;

    public void Add(MealPlanItem item)
    {
        Count++;
        TotalCalories += item.Calories;
        TotalSpGain += item.SpGain;
        FinalSp = item.NewSp; // always use the last item's NewSp
        if (item.Craving) HasCraving = true;
        TotalVarietyDeltaPp += item.VarietyDeltaPp;
        TotalTastinessDeltaPp += item.TastinessDeltaPp;
    }
}
