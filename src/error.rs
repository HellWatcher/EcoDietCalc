use thiserror::Error;

#[derive(Debug, Error)]
pub enum EcoError {
    #[error("Food not found: {0}")]
    FoodNotFound(String),

    #[error("IO error: {0}")]
    Io(#[from] std::io::Error),

    #[error("JSON error: {0}")]
    Json(#[from] serde_json::Error),

    #[error("Prompt error: {0}")]
    Prompt(#[from] dialoguer::Error),

    #[error("CSV error: {0}")]
    Csv(#[from] csv::Error),

    #[error("Invalid input: {0}")]
    InvalidInput(String),

    #[error("No available foods")]
    NoAvailableFoods,
}

pub type Result<T> = std::result::Result<T, EcoError>;
