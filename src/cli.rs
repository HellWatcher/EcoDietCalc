use clap::{Parser, Subcommand};

/// EcoDietMaker — A meal planning CLI that optimizes for nutrition, variety, and taste.
#[derive(Parser, Debug)]
#[command(name = "eco_diet_maker")]
#[command(author, version, about, long_about = None)]
pub struct Cli {
    #[command(subcommand)]
    pub command: Option<Command>,

    /// Path to the food state JSON file.
    #[arg(short, long, default_value = "food_state.json")]
    pub file: String,
}

#[derive(Subcommand, Debug)]
pub enum Command {
    /// Generate a meal plan based on available foods and constraints.
    Plan,

    /// Rate foods with unknown tastiness.
    RateUnknowns,

    /// Reset various state values.
    Reset {
        /// Reset stomach counts to 0.
        #[arg(long)]
        stomach: bool,

        /// Reset all availability to 0.
        #[arg(long)]
        availability: bool,

        /// Set all tastiness to unknown (99).
        #[arg(long)]
        tastiness: bool,
    },
}

impl Default for Command {
    fn default() -> Self {
        Command::Plan
    }
}
