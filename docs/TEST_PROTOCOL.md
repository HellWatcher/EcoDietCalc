# In-Game Validation Test Protocol

Step-by-step instructions for validating SP calculation formulas against Eco game data.

---

## Setup Requirements

1. **Fresh Eco game** or character with known starting SP
2. **Note-taking** - spreadsheet or `validation/results.csv`
3. **Tool ready**: `python main.py predict` command
4. **Console access** (optional): For checking exact SP values

---

## Pre-Test Checklist

- [ ] Record current SP before any eating
- [ ] Record game version
- [ ] Clear stomach if possible (new day)
- [ ] Ensure test foods are available in inventory

---

## Test Scenarios

### T1: Base SP + Density (Single Food, 1 Unit)

**Purpose**: Verify base SP (12) and density calculation

**Procedure**:

1. Start with empty stomach
2. Record starting SP
3. Eat 1 unit of a known food (e.g., Bannock)
4. Record new SP
5. Compare to prediction

**Expected**:

- SP delta should match: `(nutrients * (1 + bonus)) + 12`
- With empty stomach, bonus components are minimal

**Command**:

```bash
python main.py predict --food "Bannock" --quantity 1
```

---

### T2: No Variety From Same Food

**Purpose**: Verify variety doesn't increase from eating more of same food

**Procedure**:

1. Start with 1 unit of FoodX already eaten
2. Eat 2 more units of same FoodX
3. Check that variety bonus doesn't increase after threshold

**Expected**:

- Variety count stays at 1 (not 3)
- After 2000 cal threshold met, no additional variety bonus

---

### T3: Variety Bonus Activation

**Purpose**: Verify variety bonus from multiple foods

**Procedure**:

1. Eat 4 units of Food A (reaching 2000+ cal)
2. Record SP
3. Eat 4 units of Food B (reaching 2000+ cal)
4. Record SP increase

**Expected**:

- Variety should increase from 1 to 2
- Additional ~1.9 pp bonus per new qualifying food

**Command**:

```bash
python main.py predict --food "Bannock" --quantity 4
python main.py predict --food "Boiled Grains" --quantity 4 --variety-count 1
```

---

### T4: Low-Calorie Food (< 2000 cal threshold)

**Purpose**: Verify variety threshold enforcement

**Procedure**:

1. Eat a low-cal food (< 395 cal/unit) in small quantity
2. Verify it doesn't count toward variety until threshold met

**Expected**:

- Food with `calories * quantity < 2000` = no variety credit
- SP penalty may apply for ranking but not in-game SP

**Notes**:

- The `CAL_FLOOR = 395` penalty is for ranking only, not in-game

---

### T5: Favorite Food (Taste +3)

**Purpose**: Verify positive taste multiplier

**Procedure**:

1. Identify a food with tastiness = 3 (favorite)
2. Eat it with known quantity
3. Record SP
4. Compare to neutral food of same nutrients

**Expected**:

- Tastiness bonus = +30 pp contribution
- Formula: `tastiness_pp = 0.30 * 100 = 30 pp`

---

### T6: Hated Food (Taste -3)

**Purpose**: Verify negative taste multiplier

**Procedure**:

1. Identify a food with tastiness = -3 (hated)
2. Eat it with known quantity
3. Record SP

**Expected**:

- Taste bonus = -30 pp contribution
- SP should be noticeably lower than neutral

---

### T7: Satisfy 1 Craving

**Purpose**: Verify +10% craving satisfaction bonus

**Procedure**:

1. Note your active cravings (0 satisfied so far)
2. Eat the craved food (one bite satisfies)
3. Eat more food afterward and record SP gain

**Expected**:

- +10% bonus on subsequent SP gain while craving food is in stomach
- `satisfied_bonus = 1 * 0.10 = 0.10`

---

### T8: Satisfy 3 Cravings (Cap Test)

**Purpose**: Verify craving satisfaction stacks up to 3 and caps at +30%

**Procedure**:

1. Have 3 active cravings
2. Eat all 3 craved foods
3. Eat additional food and record SP gain

**Expected**:

- +30% bonus on SP gain (3 × 10%)
- 4th satisfied craving should not add more bonus
- `satisfied_bonus = 3 * 0.10 = 0.30`

---

### T9: Variety Curve Mapping

**Purpose**: Map the variety bonus curve

**Procedure**:

1. Record SP with variety count = 1
2. Progressively add new foods (meeting threshold each time)
3. Record SP at variety counts: 1, 3, 5, 7, 10, 15, 20

**Expected Values**:
| Count | Bonus (pp) |
|-------|------------|
| 1 | 1.90 |
| 5 | 8.80 |
| 10 | 16.03 |
| 15 | 21.59 |
| 20 | 27.50 |

**Note**: Use the predict command to generate expected values

---

## Recording Format

For each test, record in `validation/results.csv`:

```csv
Test_ID,Date,Game_Version,Food,Quantity,Starting_SP,Ending_SP,Actual_Delta,Predicted_Delta,Error_Pct,Notes
T1,2026-01-29,v11.0,Bannock,1,100.00,122.50,22.50,22.39,0.49%,Base SP verified
```

### Required Fields

| Field           | Description                              |
| --------------- | ---------------------------------------- |
| Test_ID         | Test case identifier (T1-T9)             |
| Date            | Test date (YYYY-MM-DD)                   |
| Game_Version    | Eco game version                         |
| Food            | Food name tested                         |
| Quantity        | Units eaten                              |
| Starting_SP     | SP before eating                         |
| Ending_SP       | SP after eating                          |
| Actual_Delta    | `Ending_SP - Starting_SP`                |
| Predicted_Delta | From predict command                     |
| Error_Pct       | `abs(actual - predicted) / actual * 100` |
| Notes           | Observations, edge cases                 |

---

## Troubleshooting

### SP Doesn't Match Prediction

1. **Check stomach state** - Did you account for existing food?
2. **Check cravings** - Are cravings active that you didn't account for?
3. **Check satisfied count** - Were cravings satisfied earlier?
4. **Server multiplier** - Is the server using a non-1.0 multiplier?
5. **Dinner party** - Is dinner party bonus active?

### Common Issues

| Symptom       | Likely Cause                                |
| ------------- | ------------------------------------------- |
| SP too high   | Missed a craving or satisfied bonus         |
| SP too low    | Stomach wasn't empty, accumulated nutrients |
| Variety wrong | Food didn't meet 2000 cal threshold         |
| Taste wrong   | Tastiness rating incorrect in data          |

---

## Success Criteria

The validation is successful when:

1. **Average error < 5%** across all tests
2. **No systematic bias** (errors random, not consistently high/low)
3. **All test cases completed** at least once
4. **Formulas documented** with verified status

---

## Post-Validation

After completing tests:

1. Update `docs/FORMULAS.md` - change [UNVERIFIED] to [VERIFIED] where confirmed
2. Document any formula corrections in commit message
3. Update constants if values differ from assumptions
4. Re-run affected tests after corrections
