using System.Collections.Generic;

namespace EcoDietMod.Discovery;

/// <summary>
/// Filter criteria for shop food discovery.
/// </summary>
public sealed record ShopFilter(List<string> CurrencyFilter, float MaxCostPer1000Cal);
