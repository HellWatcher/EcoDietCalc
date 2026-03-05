using System;
using System.Collections.Concurrent;
using System.Collections.Generic;
using System.IO;
using System.Text.Json;
using System.Text.Json.Serialization;
using Eco.Shared.Logging;

namespace EcoDietMod.Config;

/// <summary>
/// Per-player display preferences, persisted as JSON in Mods/EcoDietMod/config/.
/// </summary>
public sealed class DisplayConfig
{
    /// <summary>Plan for full stomach capacity instead of remaining calories.</summary>
    public bool FullPlan { get; set; }

    /// <summary>Compact vs full plan format.</summary>
    public bool Compact { get; set; }

    /// <summary>Show food source tags (backpack, etc).</summary>
    public bool Sources { get; set; } = true;

    /// <summary>Show variety/taste/craving tags.</summary>
    public bool Tags { get; set; }

    // --- Shop filter ---

    /// <summary>Only include shop food priced in these currencies (empty = allow all).</summary>
    public List<string> ShopCurrencyFilter { get; set; } = new();

    /// <summary>Max cost per 1000 calories from shops (0 = no limit).</summary>
    public float MaxCostPer1000Cal { get; set; }

    /// <summary>Player-configurable discovery radius in meters (99999 = effectively unlimited).</summary>
    public float MaxDiscoveryRadius { get; set; } = 99999f;

    // --- Persistence ---

    private static readonly ConcurrentDictionary<string, DisplayConfig> Cache = new(StringComparer.OrdinalIgnoreCase);

    private static readonly JsonSerializerOptions JsonOptions = new()
    {
        WriteIndented = true,
        DefaultIgnoreCondition = JsonIgnoreCondition.Never,
        PropertyNamingPolicy = JsonNamingPolicy.CamelCase
    };

    /// <summary>
    /// Load config for a player (cached after first read).
    /// </summary>
    public static DisplayConfig Load(string playerName)
    {
        return Cache.GetOrAdd(playerName, LoadFromDisk);
    }

    private static DisplayConfig LoadFromDisk(string playerName)
    {
        var path = GetPath(playerName);

        if (!File.Exists(path))
            return new DisplayConfig();

        try
        {
            var json = File.ReadAllText(path);
            return JsonSerializer.Deserialize<DisplayConfig>(json, JsonOptions) ?? new DisplayConfig();
        }
        catch (Exception ex)
        {
            Log.WriteWarningLineLocStr($"[EcoDiet] Failed to load config for '{playerName}': {ex.Message}");
            return new DisplayConfig();
        }
    }

    /// <summary>
    /// Persist current settings to disk.
    /// </summary>
    public static void Save(DisplayConfig config, string playerName)
    {
        var path = GetPath(playerName);
        var dir = Path.GetDirectoryName(path)!;
        Directory.CreateDirectory(dir);

        var json = JsonSerializer.Serialize(config, JsonOptions);
        File.WriteAllText(path, json);
        Cache[playerName] = config;
    }

    /// <summary>
    /// Convenience: save this instance for the given player.
    /// </summary>
    public void Save(string playerName) => Save(this, playerName);

    private static string GetPath(string playerName)
    {
        // Sanitize player name for filesystem
        var safeName = string.Join("_", playerName.Split(Path.GetInvalidFileNameChars()));
        return Path.Combine(
            AppDomain.CurrentDomain.BaseDirectory,
            "Mods", "EcoDietMod", "config",
            $"{safeName}.json");
    }
}
