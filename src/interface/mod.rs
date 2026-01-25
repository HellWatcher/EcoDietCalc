pub mod prompts;
pub mod render;

pub use prompts::{
    collect_user_constraints, prompt_cravings, prompt_cravings_satisfied, prompt_current_calories,
    prompt_max_calories, prompt_tastiness, prompt_yes_no,
};
pub use render::{display_food_list, display_meal_plan};
