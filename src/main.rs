use fim::{get_epigram, post_impression};

use clap::{Parser, Subcommand};
use log::debug;
use env_logger::{Builder, Target};

#[derive(Parser, Debug)]
struct Cli {
    /// The bucket to narrow filters from
    #[arg(long, short)]
    bucket: Option<String>,

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

    // todo!("make a command line option for this")
    Builder::new()
        .target(Target::Stdout)
        .parse_env("RUST_LOG")
        .init();


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

            if let Some(bucket) = &cli.bucket {
                debug!("Using bucket name: {}", bucket);
                get_impression(Some(bucket));
            }
            else {
                get_impression(None);
            }
        }
    }
}

fn get_impression(bucket : Option<&String>) {

    let post = get_epigram(bucket);

    let mut results = post.unwrap();
    debug!("{:?}", results.0.epigram_uuid);
    let output = format!(
        "\n{}\nBucket: {}\n",
        results.0.content.as_deref().unwrap_or("N/A"),
        results.1.name.as_deref().unwrap_or("No Bucket")
    );

    // Single flush to stdout
    println!("{}", output);

    post_impression(&mut results.0);
}

fn favorite() {
    //let post = get_last_epigram();
}