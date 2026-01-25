/// Represents a single item (bite) in a meal plan.
#[derive(Debug, Clone)]
pub struct MealPlanItem {
    /// Name of the food consumed.
    pub food_name: String,

    /// Calories from this bite.
    pub calories: f64,

    /// SP gained from this bite.
    pub sp_gain: f64,

    /// New total SP after this bite.
    pub new_total_sp: f64,

    /// Whether this bite satisfied a craving.
    pub is_craving: bool,

    /// Change in variety bonus (percentage points).
    pub variety_delta: f64,

    /// Change in taste bonus (percentage points).
    pub taste_delta: f64,
}

impl MealPlanItem {
    pub fn new(
        food_name: String,
        calories: f64,
        sp_gain: f64,
        new_total_sp: f64,
        is_craving: bool,
        variety_delta: f64,
        taste_delta: f64,
    ) -> Self {
        Self {
            food_name,
            calories,
            sp_gain,
            new_total_sp,
            is_craving,
            variety_delta,
            taste_delta,
        }
    }
}
