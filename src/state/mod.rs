mod manager;
mod persistence;

pub use manager::FoodStateManager;
pub use persistence::{load_foods, save_foods};
