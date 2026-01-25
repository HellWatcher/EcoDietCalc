pub mod calculations;
pub mod constants;
pub mod ranking;

pub use calculations::{
    calculate_balance_mult, calculate_craving_mult, calculate_sp, calculate_taste_mult,
    calculate_variety_mult, count_variety_qualifying, get_sp_delta, is_variety_qualifying,
    sum_all_weighted_nutrients, NutrientDensity, SpConfig,
};
pub use constants::*;
pub use ranking::{choose_next_bite, generate_plan, pick_feasible_craving};
