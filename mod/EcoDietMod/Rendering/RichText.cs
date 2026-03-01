namespace EcoDietMod.Rendering;

/// <summary>
/// TMP rich text helpers for tooltip styling.
/// Chat output should NOT use these — TMP tags are only rendered in tooltips.
/// </summary>
public static class RichText
{
    public static string Color(string text, string color) => $"<color={color}>{text}</color>";
    public static string Bold(string text) => $"<b>{text}</b>";
    public static string Size(string text, string size) => $"<size={size}>{text}</size>";

    // Color palette — high contrast on dark tooltip background
    public const string Header      = "#E0C882";  // warm gold
    public const string FoodName    = "#FFFFFF";  // white
    public const string SpPositive  = "#7FBF7F";  // soft green
    public const string SpNegative  = "#D4645C";  // soft red
    public const string SpRunning   = "#B0B0B0";  // muted gray
    public const string Calories    = "#B0B0B0";  // muted gray
    public const string Backpack    = "#C8C8C8";  // light gray
    public const string Storage     = "#82B4E0";  // soft blue
    public const string Shop        = "#D4A85C";  // amber/gold
    public const string TagCraving  = "#E0D45C";  // yellow
    public const string TagVariety  = "#82D4D4";  // cyan/teal
    public const string TagTaste    = "#C882D4";  // purple/magenta
    public const string Marker      = "#7FBF7F";  // green arrow for "eat next"
    public const string MarkerDot   = "#808080";  // dim dot for subsequent
    public const string StatusMsg   = "#B0B0B0";  // edge state messages

    /// <summary>Percentage size for tooltip content to match surrounding base text.</summary>
    public const string TooltipSize = "90%";
}
