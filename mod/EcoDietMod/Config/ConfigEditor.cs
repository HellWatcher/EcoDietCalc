using System;
using System.Linq;
using Eco.Core.Controller;
using Eco.Gameplay.Economy;
using Eco.Gameplay.Players;
using Eco.Gameplay.Systems;
using Eco.Shared.Localization;
using EcoDietMod.Tracking;

namespace EcoDietMod.Config;

/// <summary>
/// Single-window config editor using Eco's ViewEditor API.
/// Opens all display settings as form fields in one panel.
/// </summary>
public static class ConfigEditor
{
    /// <summary>
    /// Opens the ViewEditor panel for the player's display config.
    /// Fire-and-forget — ViewEditor.Edit is void.
    /// </summary>
    public static void EditInteractive(User user)
    {
        var config = DisplayConfig.Load(user.Name);
        var viewModel = CreateViewModel(config);

        ViewEditor.Edit(
            user,
            viewModel,
            onSubmit: _ => ApplyAndSave(viewModel, config, user),
            onBack: _ => user.MsgLocStr("Settings not saved."),
            buttonText: Localizer.DoStr("Save"),
            overrideTitle: Localizer.DoStr("EcoDiet Settings"),
            windowType: ViewEditor.WindowType.Small);
    }

    /// <summary>
    /// Populate a ViewModel from the current config.
    /// </summary>
    private static DisplayConfigViewModel CreateViewModel(DisplayConfig config)
    {
        var viewModel = new DisplayConfigViewModel
        {
            Compact = config.Compact,
            Sources = config.Sources,
            Tags = config.Tags,
            AutoPlan = config.AutoPlan,
            MaxCostPer1000Cal = config.MaxCostPer1000Cal,
            MaxDiscoveryRadius = config.MaxDiscoveryRadius,
        };

        // Populate currency picker from saved filter
        foreach (var name in config.ShopCurrencyFilter)
        {
            var currency = CurrencyManager.GetClosestCurrency(name);
            if (currency != null)
                viewModel.CurrencyFilter.Entries.Add(currency);
        }

        return viewModel;
    }

    /// <summary>
    /// Validate ViewModel values, copy back to config, and persist.
    /// Called by ViewEditor on Save button click.
    /// </summary>
    private static void ApplyAndSave(DisplayConfigViewModel viewModel, DisplayConfig config, User user)
    {
        try
        {
            // Booleans — no validation needed
            config.Compact = viewModel.Compact;
            config.Sources = viewModel.Sources;
            config.Tags = viewModel.Tags;
            config.AutoPlan = viewModel.AutoPlan;

            // Currencies — extract from picker
            config.ShopCurrencyFilter = viewModel.CurrencyFilter
                .GetObjects<Currency>()
                .Select(c => c.Name)
                .ToList();

            // MaxCostPer1000Cal — clamp negatives to 0
            config.MaxCostPer1000Cal = Math.Max(0f, viewModel.MaxCostPer1000Cal);

            // MaxDiscoveryRadius — only clamp minimum (no upper cap)
            config.MaxDiscoveryRadius = Math.Max(1f, viewModel.MaxDiscoveryRadius);

            config.Save(user.Name);
            PlanTracker.ClearPlan(user);
            user.MsgLocStr("Settings saved.");
        }
        catch (Exception ex)
        {
            user.MsgLocStr($"Error saving config: {ex.Message}");
        }
    }
}
