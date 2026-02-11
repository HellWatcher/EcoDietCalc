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

| Parameter           | Default | Description                                                       |
| ------------------- | ------- | ----------------------------------------------------------------- |
| `BASE_SP`           | 12      | **[UNVERIFIED]** Base skill points added before server multiplier |
| `server_mult`       | 1.0     | Server skill gain multiplier                                      |
| `dinner_party_mult` | 1.0     | Dinner party bonus (1.0 to 3.0)                                   |

### Expanded Formula

```
SP = ((D * (1 + B/100 + V/100 + T/100 + S) * dinner_party) + 12) * server_mult

where:
  D = density_sum (calorie-weighted nutrient average)
  B = balance bonus (pp)
  V = variety bonus (pp)
  T = tastiness bonus (pp)
  S = satisfied craving bonus (fraction, 0.10 per satisfied craving)
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

density_sum = carbs + protein + fat + vitamins
```

### Example

| Food          | Qty | Calories | Carbs | Protein | Fat | Vitamins |
| ------------- | --- | -------- | ----- | ------- | --- | -------- |
| Bannock       | 2   | 650      | 6     | 5       | 7   | 4        |
| Boiled Grains | 1   | 480      | 7     | 6       | 1   | 7        |

Total calories: 2*650 + 1*480 = 1780

```
weight_bannock = 1300/1780 = 0.730
weight_grains = 480/1780 = 0.270

density_carbs = 6*0.730 + 7*0.270 = 6.27
density_protein = 5*0.730 + 6*0.270 = 5.27
density_fat = 7*0.730 + 1*0.270 = 5.38
density_vitamins = 4*0.730 + 7*0.270 = 4.81

density_sum = 6.27 + 5.27 + 5.38 + 4.81 = 21.73
```

---

## 2. Balance Bonus

**Location**: `calculations.py:calculate_balanced_diet_bonus()`, `calculate_balanced_diet_ratio()`

### Definition

```
ratio = min(nutrients) / max(nutrients)    # includes zeros!
balanced_diet_pp = (ratio * 100) - 50
```

> **Verified**: A zero nutrient (e.g. fat=0) gives ratio=0, pp=-50.
> The game's `BalancedDietMult` = 0.5 + ratio\*0.5, which equals `(100 + pp) / 100`.

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

balanced_diet_pp = (0.767 * 100) - 50 = 26.7 pp
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

| Constant                | Value    | Status                                        |
| ----------------------- | -------- | --------------------------------------------- |
| `VARIETY_BONUS_CAP_PP`  | 55       | **[UNVERIFIED]** Asymptotic cap               |
| `VARIETY_CAL_THRESHOLD` | 2000     | **[UNVERIFIED]** Calories per food to qualify |
| Half-life               | 20 foods | **[UNVERIFIED]** Count to reach half of cap   |

### Qualifying Foods

A food counts toward variety only if:

```
calories * quantity >= VARIETY_CAL_THRESHOLD (2000)
```

**[UNVERIFIED]**: Threshold is exactly 2000 calories

### Example Values

| Count | Variety Bonus (pp) |
| ----- | ------------------ |
| 0     | 0.00               |
| 1     | 1.90               |
| 5     | 8.80               |
| 10    | 16.03              |
| 20    | 27.50              |
| 40    | 41.25              |
| 60    | 48.13              |

---

## 4. Tastiness Bonus

**Location**: `calculations.py:get_tastiness_bonus()`

### Definition

Calorie-weighted average of tastiness multipliers:

```
taste_score = sum(TASTINESS_MULTIPLIER[food.tastiness] * food.calories * quantity)
              / total_calories

tastiness_pp = taste_score * 100 * TASTINESS_WEIGHT
```

### Tastiness Multipliers

**Location**: `constants.py:TASTINESS_MULTIPLIERS`

| Tastiness | Label     | Multiplier |
| --------- | --------- | ---------- |
| -3        | worst     | -0.30      |
| -2        | horrible  | -0.20      |
| -1        | bad       | -0.10      |
| 0         | ok        | 0.00       |
| 1         | good      | +0.10      |
| 2         | delicious | +0.20      |
| 3         | favorite  | +0.30      |
| 99        | unknown   | 0.00       |

**[UNVERIFIED]**: Multiplier scale of [-0.30, +0.30]

### Range

With `TASTINESS_WEIGHT = 1.0`:

- **Minimum**: -30 pp (all worst foods)
- **Maximum**: +30 pp (all favorite foods)

### Example

| Food          | Qty | Calories | Tastiness     | Multiplier |
| ------------- | --- | -------- | ------------- | ---------- |
| Bannock       | 2   | 650      | 2 (delicious) | +0.20      |
| Boiled Grains | 1   | 480      | 0 (ok)        | 0.00       |

```
total_cal = 1780
taste_score = (0.20 * 1300 + 0.00 * 480) / 1780 = 0.146
tastiness_pp = 0.146 * 100 * 1.0 = 14.6 pp
```

---

## 5. Satisfied Craving Bonus

**Location**: `calculations.py:get_sp()`

### Definition

Bonus applied when cravings were satisfied earlier in the day:

```
satisfied_bonus = cravings_satisfied * CRAVING_SATISFIED_FRAC
```

### Constants

| Constant                 | Value | Status                                          |
| ------------------------ | ----- | ----------------------------------------------- |
| `CRAVING_SATISFIED_FRAC` | 0.10  | **[UNVERIFIED]** Fraction per satisfied craving |

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
balanced_diet_pp = (0.571 * 100) - 50 = 7.14 pp
```

### Step 3: Variety

```
total_calories = 4 * 650 = 2600 >= 2000 threshold
count = 1
variety_pp = 55 * (1 - 0.5^(1/20)) = 1.90 pp
```

### Step 4: Tastiness

```
tastiness_pp = 0.20 * 100 * 1.0 = 20.0 pp
```

### Step 5: Satisfied Cravings (none)

```
satisfied_bonus = 0
```

### Step 6: Final SP

```
bonus = (7.14 + 1.90 + 20.0) / 100 + 0 = 0.2904
nutrition_sp = 22.0 * (1 + 0.2904) * 1.0 = 28.39
SP = (28.39 + 12) * 1.0 = 40.39
```

---

## Validation Checklist

| Component         | Assumption         | Test Case                    |
| ----------------- | ------------------ | ---------------------------- |
| Base SP           | = 12               | T1: Single food, verify base |
| Variety threshold | = 2000 cal         | T4: Low-cal food test        |
| Variety cap       | = 55 pp            | T11: Map variety curve       |
| Taste scale       | [-0.30, +0.30]     | T5, T6: Favorite/hated foods |
| Satisfied frac    | = 0.10 per craving | T7, T8: Craving satisfaction |
| Balance range     | [-50, +50]         | Integration tests            |

---

## Code References

| File              | Function                           | Purpose               |
| ----------------- | ---------------------------------- | --------------------- |
| `calculations.py` | `get_sp()`                         | Master SP calculation |
| `calculations.py` | `sum_all_weighted_nutrients()`     | Density computation   |
| `calculations.py` | `calculate_balanced_diet_bonus()`  | Balanced diet pp      |
| `calculations.py` | `get_variety_bonus()`              | Variety pp            |
| `calculations.py` | `get_tastiness_bonus()`            | Tastiness pp          |
| `calculations.py` | `calculate_nutrition_multiplier()` | Combined bonus        |
| `constants.py`    | All constants                      | Tuneable parameters   |
