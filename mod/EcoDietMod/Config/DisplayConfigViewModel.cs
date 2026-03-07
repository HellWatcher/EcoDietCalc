using System.ComponentModel;
using Eco.Core.Controller;
using Eco.Core.Systems;
using Eco.Gameplay.Civics.GameValues;
using Eco.Gameplay.Economy;
using Eco.Shared.Localization;
using Eco.Shared.Networking;
using Eco.Shared.Serialization;
using Eco.Shared.View;

namespace EcoDietMod.Config;

/// <summary>
/// Transient ViewModel for ViewEditor — mirrors <see cref="DisplayConfig"/> as attributed properties.
/// Booleans are exposed as int (0 = off, 1 = on) because [Autogen] IL-weaves a client-only checkbox
/// for bool properties that never fires the [AutoRPC] RPC. Int forces a text-input widget that does.
/// </summary>
[Serialized, AutogenClass]
public class DisplayConfigViewModel : IController, IViewController, IHasUniversalID, INotifyPropertyChanged
{
    private int _controllerID;
    public ref int ControllerID => ref _controllerID;

    // --- Booleans as int (0/1): forces text-input widget that fires RPCs ---

    private int _fullPlan;
    [SyncToView, Autogen, AutoRPC, LocDisplayName("Full Plan (0/1)"),
     LocDescription("Plan for full stomach capacity (empty stomach sim) instead of remaining calories. 0 = remaining, 1 = full.")]
    public int FullPlanInt
    {
        get => _fullPlan;
        set { _fullPlan = value != 0 ? 1 : 0; this.Changed(nameof(FullPlanInt)); }
    }

    private int _compact;
    [SyncToView, Autogen, AutoRPC, LocDisplayName("Compact (0/1)"),
     LocDescription("Shorten plan output — hides SP breakdown, shows only food name and calorie count per bite. 0 = off, 1 = on.")]
    public int CompactInt
    {
        get => _compact;
        set { _compact = value != 0 ? 1 : 0; this.Changed(nameof(CompactInt)); }
    }

    private int _sources;
    [SyncToView, Autogen, AutoRPC, LocDisplayName("Sources (0/1)"),
     LocDescription("Show where each food comes from — [backpack], [StorageName @ 15m], [ShopName @ 30m]. 0 = off, 1 = on.")]
    public int SourcesInt
    {
        get => _sources;
        set { _sources = value != 0 ? 1 : 0; this.Changed(nameof(SourcesInt)); }
    }

    private int _tags;
    [SyncToView, Autogen, AutoRPC, LocDisplayName("Tags (0/1)"),
     LocDescription("Show scoring tags on each bite — [variety +2pp], [craving], [delicious]. 0 = off, 1 = on.")]
    public int TagsInt
    {
        get => _tags;
        set { _tags = value != 0 ? 1 : 0; this.Changed(nameof(TagsInt)); }
    }

    // --- Convenience accessors for bool semantics (not synced to view) ---

    public bool FullPlan { get => _fullPlan != 0; set => FullPlanInt = value ? 1 : 0; }
    public bool Compact { get => _compact != 0; set => CompactInt = value ? 1 : 0; }
    public bool Sources { get => _sources != 0; set => SourcesInt = value ? 1 : 0; }
    public bool Tags { get => _tags != 0; set => TagsInt = value ? 1 : 0; }

    // --- Non-booleans: keep [Autogen] + [AutoRPC] (working) ---

    [SyncToView, Autogen, AutoRPC, LocDisplayName("Shop Currencies"),
     LocDescription("Only include shop food priced in these currencies. Leave empty to allow all currencies.")]
    public GamePickerList CurrencyFilter { get; set; }

    private float _maxCostPer1000Cal;
    [SyncToView, Autogen, AutoRPC, LocDisplayName("Max Cost/1000cal"),
     LocDescription("Exclude shop food costing more than this per 1000 calories. Set to 0 to disable the cost filter.")]
    public float MaxCostPer1000Cal
    {
        get => _maxCostPer1000Cal;
        set { _maxCostPer1000Cal = value; this.Changed(nameof(MaxCostPer1000Cal)); }
    }

    private float _maxDiscoveryRadius;
    [SyncToView, Autogen, AutoRPC, LocDisplayName("Max Distance"),
     LocDescription("How far (in meters) to search for food in storage containers and shops. Default: unlimited.")]
    public float MaxDiscoveryRadius
    {
        get => _maxDiscoveryRadius;
        set { _maxDiscoveryRadius = value; this.Changed(nameof(MaxDiscoveryRadius)); }
    }

    private float _minCalorieFloor;
    [SyncToView, Autogen, AutoRPC, LocDisplayName("Min Calories"),
     LocDescription("Skip foods with this many calories or fewer. Default: 120.")]
    public float MinCalorieFloor
    {
        get => _minCalorieFloor;
        set { _minCalorieFloor = value; this.Changed(nameof(MinCalorieFloor)); }
    }

    public event PropertyChangedEventHandler? PropertyChanged;

    public DisplayConfigViewModel()
    {
        CurrencyFilter = new GamePickerList(typeof(Currency));
    }
}
