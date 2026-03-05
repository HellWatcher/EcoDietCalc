namespace EcoDietMod.Models;

/// <summary>
/// A single source contribution for a food item (source + quantity available there).
/// </summary>
public sealed record SourceEntry(SourceInfo Source, int Quantity);
