use fim::{get_epigram, post_impression};

use clap::{Parser, Subcommand};

#[derive(Parser, Debug)]
struct Cli {
    /// Your OpenAI API Token
    #[arg(long, short)]
    openai: Option<String>,

    /// Query ChatGPT to get context about this epigram
    #[arg(long, action)]
    gpt: bool,

    #[command(subcommand)]
    command: Option<Commands>,
}

#[derive(Subcommand, Debug)]
enum Commands {
    /// Import data from a specified source
    Import {
        #[arg(value_enum)]
        source_type: SourceType,

        /// Path to the file or directory to import
        #[arg(value_name = "PATH")]
        path: String,
    },

    /// Generate context
    Context {
        /// Your OpenAI API Token
        #[arg(long, value_name = "TOKEN")]
        openai: Option<String>,
    },

    /// Save the previous impression into favorites
    Favorite {},

    /// Chat with the model
    Chat {},
}

#[derive(clap::ValueEnum, Clone, Debug, )]
enum SourceType {
    Fortune,
}

fn main() {
    let cli = Cli::parse();

    match &cli.command {
        Some(Commands::Import { source_type, path }) => {
            println!("Importing {:?} from path: {}", source_type, path);
        }
        Some(Commands::Context { openai  }) => {
            println!("Generating context with OpenAI Token: {:?}", openai);
            // Handle context generation here
        }
        Some(Commands::Favorite {}) => {
            println!("Saving current state...");
            // Handle save functionality here
        }
        Some(Commands::Chat {}) => {
            println!("Starting chat...");
            // Handle chat functionality here
        }
        None => {
            get_impression();
        }
    }
}

fn get_impression() {

    let post = get_epigram();
    println!("{}", post.0.epigram_uuid);
    println!("-----------");
    println!("{}", post.0.content.as_deref().unwrap_or("N/A"));
    println!("{:#?}", post.1.name);

    post_impression(&post.0);
}

