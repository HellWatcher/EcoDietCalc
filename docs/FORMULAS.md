# SP Calculation Formulas

Documentation of all Skill Point (SP) calculation formulas used in the Eco Diet Maker.

> **Status**: Formulas extracted from code. Marked assumptions need in-game validation.

---

## Master SP Formula

**Location**: `calculations.py:get_sp()`

```
SP = (nutrition_sp + BASE_SP) * server_mult

where:
  nutrition_sp = density_sum * (1 + bonus) * dinner_party_mult
  bonus = nutrition_multiplier / 100 + satisfied_bonus
```

### Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `BASE_SP` | 12 | **[UNVERIFIED]** Base skill points added before server multiplier |
| `server_mult` | 1.0 | Server skill gain multiplier |
| `dinner_party_mult` | 1.0 | Dinner party bonus (1.0 to 3.0) |

### Expanded Formula

```
SP = ((D * (1 + B/100 + V/100 + T/100 + C/100 + S) * dinner_party) + 12) * server_mult

where:
  D = density_sum (calorie-weighted nutrient average)
  B = balance bonus (pp)
  V = variety bonus (pp)
  T = taste bonus (pp)
  C = craving match bonus (pp)
  S = satisfied craving bonus (fraction)
```

---

## 1. Density (Nutrient Sum)

**Location**: `calculations.py:sum_all_weighted_nutrients()`

### Definition

Calorie-weighted average of all nutrients in the stomach.

```
For each food i in stomach:
  weight_i = (calories_i * quantity_i) / total_calories

density[nutrient] = sum(food_i.nutrient * weight_i)

density_sum = carbs + protein + fats + vitamins
```

### Example

| Food | Qty | Calories | Carbs | Protein | Fats | Vitamins |
|------|-----|----------|-------|---------|------|----------|
| Bannock | 2 | 650 | 6 | 5 | 7 | 4 |
| Boiled Grains | 1 | 480 | 7 | 6 | 1 | 7 |

Total calories: 2*650 + 1*480 = 1780

```
weight_bannock = 1300/1780 = 0.730
weight_grains = 480/1780 = 0.270

density_carbs = 6*0.730 + 7*0.270 = 6.27
density_protein = 5*0.730 + 6*0.270 = 5.27
density_fats = 7*0.730 + 1*0.270 = 5.38
density_vitamins = 4*0.730 + 7*0.270 = 4.81

density_sum = 6.27 + 5.27 + 5.38 + 4.81 = 21.73
```

---

## 2. Balance Bonus

**Location**: `calculations.py:calculate_balance_bonus()`, `calculate_balance_ratio()`

### Definition

```
ratio = min_nonzero(nutrients) / max(nutrients)
balance_pp = (ratio * 100) - 50
```

### Range

- **Minimum**: -50 pp (one nutrient dominates completely)
- **Maximum**: +50 pp (perfect balance, ratio = 1.0)

**[UNVERIFIED]**: Range is [-50, +50] pp

### Example

From density example above:
```
nutrients = [6.27, 5.27, 5.38, 4.81]
min_nonzero = 4.81
max = 6.27
ratio = 4.81 / 6.27 = 0.767

balance_pp = (0.767 * 100) - 50 = 26.7 pp
```

---

## 3. Variety Bonus

**Location**: `calculations.py:get_variety_bonus()`

### Definition

Exponential curve approaching cap:

```
variety_pp = VARIETY_BONUS_CAP_PP * (1 - 0.5^(count / 20))
```

### Constants

| Constant | Value | Status |
|----------|-------|--------|
| `VARIETY_BONUS_CAP_PP` | 55 | **[UNVERIFIED]** Asymptotic cap |
| `VARIETY_CAL_THRESHOLD` | 2000 | **[UNVERIFIED]** Calories per food to qualify |
| Half-life | 20 foods | **[UNVERIFIED]** Count to reach half of cap |

### Qualifying Foods

A food counts toward variety only if:
```
calories * quantity >= VARIETY_CAL_THRESHOLD (2000)
```

**[UNVERIFIED]**: Threshold is exactly 2000 calories

### Example Values

| Count | Variety Bonus (pp) |
|-------|-------------------|
| 0 | 0.00 |
| 1 | 1.90 |
| 5 | 8.80 |
| 10 | 16.03 |
| 20 | 27.50 |
| 40 | 41.25 |
| 60 | 48.13 |

---

## 4. Taste Bonus

**Location**: `calculations.py:get_taste_bonus()`

### Definition

Calorie-weighted average of tastiness multipliers:

```
taste_score = sum(TASTINESS_MULTIPLIER[food.tastiness] * food.calories * quantity)
              / total_calories

taste_pp = taste_score * 100 * TASTE_WEIGHT
```

### Tastiness Multipliers

**Location**: `constants.py:TASTINESS_MULTIPLIERS`

| Tastiness | Label | Multiplier |
|-----------|-------|------------|
| -3 | hated | -0.30 |
| -2 | horrible | -0.20 |
| -1 | bad | -0.10 |
| 0 | neutral | 0.00 |
| 1 | good | +0.10 |
| 2 | great | +0.20 |
| 3 | favorite | +0.30 |
| 99 | unknown | 0.00 |

**[UNVERIFIED]**: Multiplier scale of [-0.30, +0.30]

### Range

With `TASTE_WEIGHT = 1.0`:
- **Minimum**: -30 pp (all hated foods)
- **Maximum**: +30 pp (all favorite foods)

### Example

| Food | Qty | Calories | Tastiness | Multiplier |
|------|-----|----------|-----------|------------|
| Bannock | 2 | 650 | 2 (great) | +0.20 |
| Boiled Grains | 1 | 480 | 0 (neutral) | 0.00 |

```
total_cal = 1780
taste_score = (0.20 * 1300 + 0.00 * 480) / 1780 = 0.146
taste_pp = 0.146 * 100 * 1.0 = 14.6 pp
```

---

## 5. Craving Match Bonus

**Location**: `calculations.py:calculate_nutrition_multiplier()`

### Definition

Per-food bonus when eating a craving:

```
craving_match_count = count(foods in stomach that match active cravings)
craving_pp = min(craving_match_count, CRAVING_MAX_COUNT) * CRAVING_BONUS_PP
```

### Constants

| Constant | Value | Status |
|----------|-------|--------|
| `CRAVING_BONUS_PP` | 30 | **[UNVERIFIED]** PP per matching craving |
| `CRAVING_MAX_COUNT` | 3 | **[UNVERIFIED]** Maximum counted matches |

### Range

- **Minimum**: 0 pp (no cravings satisfied)
- **Maximum**: 90 pp (3 cravings satisfied)

**[UNVERIFIED]**: +30 pp per craving, max +90 pp

### Craving Eligibility

A food can become a craving if it meets ALL criteria:

```
calories >= CRAVING_MIN_CALORIES (500)
AND tastiness >= CRAVING_MIN_TASTINESS (1 = "good")
AND sum_nutrients() >= CRAVING_MIN_NUTRIENT_SUM (24)
```

---

## 6. Satisfied Craving Multiplier

**Location**: `calculations.py:get_sp()`

### Definition

Bonus applied when cravings were satisfied earlier in the day:

```
satisfied_bonus = cravings_satisfied * CRAVING_SATISFIED_FRAC
```

### Constants

| Constant | Value | Status |
|----------|-------|--------|
| `CRAVING_SATISFIED_FRAC` | 0.10 | **[UNVERIFIED]** Fraction per satisfied craving |

### Range

- **Minimum**: 0.00 (no previous satisfactions)
- **Maximum**: 0.30 (3 previously satisfied)

**[UNVERIFIED]**: +10% per satisfied craving

### Example

If 2 cravings were satisfied earlier:
```
satisfied_bonus = 2 * 0.10 = 0.20 (added to bonus fraction)
```

---

## Complete Example Calculation

**Scenario**: Fresh stomach, eating 4 Bannock (Bannock: 650 cal, C:6 P:5 F:7 V:4, tastiness=2)

### Step 1: Density
```
density = 6 + 5 + 7 + 4 = 22.0 (single food, no weighting needed)
```

### Step 2: Balance
```
nutrients = [6, 5, 7, 4]
ratio = 4/7 = 0.571
balance_pp = (0.571 * 100) - 50 = 7.14 pp
```

### Step 3: Variety
```
total_calories = 4 * 650 = 2600 >= 2000 threshold
count = 1
variety_pp = 55 * (1 - 0.5^(1/20)) = 1.90 pp
```

### Step 4: Taste
```
taste_pp = 0.20 * 100 * 1.0 = 20.0 pp
```

### Step 5: Craving (none active)
```
craving_pp = 0 pp
satisfied_bonus = 0
```

### Step 6: Final SP
```
bonus = (7.14 + 1.90 + 20.0 + 0) / 100 + 0 = 0.2904
nutrition_sp = 22.0 * (1 + 0.2904) * 1.0 = 28.39
SP = (28.39 + 12) * 1.0 = 40.39
```

---

## Validation Checklist

| Component | Assumption | Test Case |
|-----------|-----------|-----------|
| Base SP | = 12 | T1: Single food, verify base |
| Variety threshold | = 2000 cal | T4: Low-cal food test |
| Variety cap | = 55 pp | T11: Map variety curve |
| Taste scale | [-0.30, +0.30] | T5, T6: Favorite/hated foods |
| Craving bonus | = 30 pp each | T7: Satisfy 1 craving |
| Craving max | = 3 | T8: Satisfy 3+ cravings |
| Satisfied frac | = 0.10 | T9, T10: Daily satisfaction |
| Balance range | [-50, +50] | Integration tests |

---

## Code References

| File | Function | Purpose |
|------|----------|---------|
| `calculations.py` | `get_sp()` | Master SP calculation |
| `calculations.py` | `sum_all_weighted_nutrients()` | Density computation |
| `calculations.py` | `calculate_balance_bonus()` | Balance pp |
| `calculations.py` | `get_variety_bonus()` | Variety pp |
| `calculations.py` | `get_taste_bonus()` | Taste pp |
| `calculations.py` | `calculate_nutrition_multiplier()` | Combined bonus |
| `constants.py` | All constants | Tuneable parameters |
