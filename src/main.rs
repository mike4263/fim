use fim::{add_epigram, get_epigram, get_last_epigram, post_impression, run_migrations, save_last_epigram};

use clap::{Parser, Subcommand};
use log::debug;
use env_logger::{Builder, Target};
use textwrap::{fill};
use std::fs;
use std::io::{self, BufRead};
use std::path::Path;
use std::error::Error;

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

    /// setup the database with loaded fortunes
    Setup {},

    /// Chat with the model
    Chat {},
}

#[derive(clap::ValueEnum, Clone, Debug, )]
enum SourceType {
    Fortune,
}


#[tokio::main]
async fn main() {
    let cli = Cli::parse();

    // todo!("make a command line option for this")
    Builder::new()
        .target(Target::Stdout)
        .parse_env("RUST_LOG")
        .init();


    match &cli.command {
        Some(Commands::Import { source_type, path }) => {
            println!("Importing {:?} from path: {}", source_type, path);

            match import(Path::new(path)) {
                Ok(count) => {
                    println!("Imported {} fortunes", count);
                }
                Err(err) => {
                    eprintln!("Imported error: {}", err);
                    exit(1);
                },
            }

        }
        Some(Commands::Context { openai  }) => {
            let epigram = get_last_epigram().unwrap();

            let character = "-";
            let line_width = 80;
            let line = character.repeat(line_width);

            println!("{}\n\n{}\n", epigram.content.clone().unwrap(), line);
            let result = wait_with_spinner(context(&epigram)).await;
            match result {
                Ok(msg) => {

                    let formatted_chat = fill(&msg, line_width);
                    println!("{}", formatted_chat);
                },
                Err(e) => eprintln!("Error: {}", e),
            }
        }
        Some(Commands::Favorite {}) => {
            favorite();
        }
        Some(Commands::Chat {}) => {
            println!("Starting chat...");
            // Handle chat functionality here
        }
        Some(Commands::Setup {}) => {
            println!("Configuring database");
            let results = run_migrations();
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
    let result = save_last_epigram();

    match result {
        Ok(_) => {
            println!("Saved!")
        }
        Err(err) => {
            eprintln!("Failed to save last epigram! {:?}", err);
        }
    }
}

use std::env;
use std::process::exit;
use std::sync::Arc;
use std::time::Duration;
use dotenvy::dotenv;
use indicatif::{ProgressBar, ProgressStyle};
use openai::{
    chat::{ChatCompletion, ChatCompletionMessage, ChatCompletionMessageRole},
    set_key,
};
use tokio::sync::Notify;
use tokio::task;
use fim::models::Epigram;

async fn context(epigram : &Epigram) -> Result<String, Box<dyn std::error::Error>> {
    // Make sure you have a file named `.env` with the `OPENAI_KEY` environment variable defined!
    dotenv().unwrap();
    set_key(env::var("OPENAI_API_KEY").unwrap());
    //set_base_url(env::var("OPENAI_BASE_URL").unwrap_or_default());

    let mut messages = vec![ChatCompletionMessage {
        role: ChatCompletionMessageRole::System,
        content: Some("This output is from an application that is designed to display pithy, insightful, meaningful epigrams to users.
    Please explain this epigram, including any information about individuals referenced within, explaining the humor,
    identifying the origin.  If possible, cite any references of this in popular culture. ".to_string()),
        name: None,
        function_call: None,
    }];

    messages.push(ChatCompletionMessage {
        role: ChatCompletionMessageRole::User,
        content: Some(epigram.content.clone().unwrap()),
        name: None,
        function_call: None,
    });

    let chat_completion = ChatCompletion::builder("gpt-4o", messages.clone())
        .create()
        .await
        .unwrap();
    let returned_message = chat_completion.choices.first().unwrap().message.clone();

    Ok(returned_message.content.clone().unwrap().trim().parse().unwrap())
}



async fn wait_with_spinner<F, R>(async_op: F) -> R
where
    F: std::future::Future<Output = R>,
{
    let pb = ProgressBar::new_spinner();

    pb.enable_steady_tick(Duration::from_millis(120));
    pb.set_style(
        ProgressStyle::with_template("{spinner:.blue} {msg}")
            .unwrap()
            // For more spinners check out the cli-spinners project:
            // https://github.com/sindresorhus/cli-spinners/blob/master/spinners.json
            .tick_strings(&[
                "▹ ▹ ▹ ▹ ▹",
                "▸ ▹ ▹ ▹ ▹",
                "▹ ▸ ▹ ▹ ▹",
                "▹ ▹ ▸ ▹ ▹",
                "▹ ▹ ▹ ▸ ▹",
                "▹ ▹ ▹ ▹ ▸",
                "▪ ▪ ▪ ▪ ▪",
            ]),
    );
    pb.set_message("Asking ChatGPT...");

    // Shared notification to stop the spinner
    let notify = Arc::new(Notify::new());
    let spinner_notify = notify.clone();

    // Spawn a task to handle the spinner's lifecycle
    let spinner_handle = task::spawn_blocking(move || {
        tokio::runtime::Builder::new_current_thread()
            .build()
            .unwrap()
            .block_on(async {
                spinner_notify.notified().await;
                //pb.finish_with_message("Done!");
            });
    });

    // Await the async operation
    let result = async_op.await;

    // Notify the spinner task to finish
    notify.notify_one();

    // Wait for the spinner task to complete
    let _ = spinner_handle.await;

    // Return the result of the async operation
    result
}


fn import(directory : &Path) -> Result<i32, Box<dyn std::error::Error>> {

    // Attempt to read the directory
    let entries = fs::read_dir(directory).map_err(|_| "could not read files")?;
    let mut count : i32 = 0;

    for entry in entries {
        let entry = entry?;
        let path = entry.path();


        // Only process files, not directories
        if path.is_file() {
            debug!("Processing {:?}", path);
            if let Ok(file) = fs::File::open(&path) {
                let reader = io::BufReader::new(file);
                let mut fortune = String::new();

                for line in reader.lines() {
                    let line = line?;
                    if line == "%" {
                        
                        if !fortune.is_empty() {
                            let epigram = fortune.trim();
                            debug!("Parsed Epigram:\n{}", epigram);
                            add_epigram(epigram.parse().unwrap()).expect("TODO: panic message");
                            fortune.clear();
                            count += 1;
                        }
                    } else {
                        fortune.push_str(&line);
                        fortune.push('\n');
                        // Process data line
                    }
                }
            } else {
                eprintln!("could not read file: {}", path.display());
            }
        }
    }

    Ok(count)

}