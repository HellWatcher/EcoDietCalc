using System;
using System.Collections.Generic;
using System.IO;
using System.Text.Json;
using System.Text.Json.Serialization;

namespace EcoDietMod.Config;

/// <summary>
/// Per-player display preferences, persisted as JSON in Mods/EcoDietMod/config/.
/// </summary>
public sealed class DisplayConfig
{
    /// <summary>Compact vs full plan format.</summary>
    public bool Compact { get; set; }

    /// <summary>Show food source tags (backpack, etc).</summary>
    public bool Sources { get; set; } = true;

    /// <summary>Show variety/taste/craving tags.</summary>
    public bool Tags { get; set; } = true;

    /// <summary>Reserved for future auto-plan on food eaten.</summary>
    public bool AutoPlan { get; set; }

    // --- Persistence ---

    private static readonly Dictionary<string, DisplayConfig> Cache = new(StringComparer.OrdinalIgnoreCase);

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
        if (Cache.TryGetValue(playerName, out var cached))
            return cached;

        var path = GetPath(playerName);
        DisplayConfig config;

        if (File.Exists(path))
        {
            try
            {
                var json = File.ReadAllText(path);
                config = JsonSerializer.Deserialize<DisplayConfig>(json, JsonOptions) ?? new DisplayConfig();
            }
            catch
            {
                config = new DisplayConfig();
            }
        }
        else
        {
            config = new DisplayConfig();
        }

        Cache[playerName] = config;
        return config;
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
