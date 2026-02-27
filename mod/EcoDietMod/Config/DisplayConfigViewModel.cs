using Eco.Core.Controller;
using Eco.Core.Systems;
using Eco.Gameplay.Civics.GameValues;
using Eco.Gameplay.Economy;
using Eco.Shared.Localization;
using Eco.Shared.Networking;
using Eco.Shared.View;

namespace EcoDietMod.Config;

/// <summary>
/// Transient ViewModel for ViewEditor — mirrors <see cref="DisplayConfig"/> as attributed properties.
/// ViewEditor renders all [SyncToView] properties as form fields in a single window.
/// [AutoRPC] registers Set{PropertyName} RPCs with ControllerMarshalerService so the client
/// can push edits back to the server. Manual Set* methods are NOT needed when [AutoRPC] is present.
/// </summary>
[AutogenClass]
public class DisplayConfigViewModel : IController, IViewController, IHasUniversalID
{
    private int _controllerID;
    public ref int ControllerID => ref _controllerID;

    // --- Properties: [AutoRPC] creates the Set{Name} RPC from the property setter ---

    private bool _compact;
    [SyncToView, Autogen, AutoRPC, LocDisplayName("Compact"),
     LocDescription("Shorten plan output — hides SP breakdown, shows only food name and calorie count per bite")]
    public bool Compact
    {
        get => _compact;
        set { _compact = value; this.Changed(nameof(Compact)); }
    }

    private bool _sources;
    [SyncToView, Autogen, AutoRPC, LocDisplayName("Sources"),
     LocDescription("Show where each food comes from — [backpack], [StorageName @ 15m], [ShopName @ 30m]")]
    public bool Sources
    {
        get => _sources;
        set { _sources = value; this.Changed(nameof(Sources)); }
    }

    private bool _tags;
    [SyncToView, Autogen, AutoRPC, LocDisplayName("Tags"),
     LocDescription("Show scoring tags on each bite — [variety +2pp], [craving], [delicious]")]
    public bool Tags
    {
        get => _tags;
        set { _tags = value; this.Changed(nameof(Tags)); }
    }

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

    public DisplayConfigViewModel()
    {
        CurrencyFilter = new GamePickerList(typeof(Currency));
    }
}
