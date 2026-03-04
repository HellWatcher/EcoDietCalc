using System;
using Eco.Gameplay.Objects;
using EcoDietMod.Rendering;

namespace EcoDietMod.Models;

/// <summary>
/// Kind of food source discovered during planning.
/// </summary>
public enum SourceKind
{
    Backpack,
    Storage,
    Shop
}

/// <summary>
/// Describes where a food item was found — backpack, storage container, or shop.
/// Sortable by distance (backpack = 0).
/// </summary>
public sealed class SourceInfo : IComparable<SourceInfo>
{
    public SourceKind Kind { get; }
    public string Label { get; }
    public float DistanceMeters { get; }
    public float? PricePerUnit { get; init; }
    public string? Currency { get; init; }
    public WorldObject? WorldObj { get; init; }

    public SourceInfo(SourceKind kind, string label, float distanceMeters)
    {
        Kind = kind;
        Label = label;
        DistanceMeters = distanceMeters;
    }

    /// <summary>
    /// Display tag for rendering, e.g. "[backpack]" or "[Refrigerator @ 15m]".
    /// </summary>
    public string Tag => Kind switch
    {
        SourceKind.Backpack => "[backpack]",
        SourceKind.Storage  => $"[{Label} @ {DistanceMeters:F0}m]",
        SourceKind.Shop     => $"[{Label} @ {DistanceMeters:F0}m]",
        _                   => $"[{Label}]"
    };

    /// <summary>
    /// Tag wrapped in source-kind-appropriate TMP color for tooltip rendering.
    /// </summary>
    public string ColoredTag => Kind switch
    {
        SourceKind.Backpack => RichText.Color(Tag, RichText.Backpack),
        SourceKind.Storage  => RichText.Color(Tag, RichText.Storage),
        SourceKind.Shop     => RichText.Color(Tag, RichText.Shop),
        _                   => Tag
    };

    public int CompareTo(SourceInfo? other) =>
        DistanceMeters.CompareTo(other?.DistanceMeters ?? float.MaxValue);
}
