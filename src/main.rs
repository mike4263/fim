use fim::{add_epigram, get_epigram, get_last_epigram, get_random_epigram, lookup_or_add_bucket_by_name, post_impression, run_migrations, save_last_epigram};

use clap::{Parser, Subcommand};
use env_logger::{Builder, Target};
use log::debug;
use std::path::Path;
use textwrap::fill;
use tokio::fs;
use tokio::io;

use sqlx::sqlite::SqlitePool;


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
async fn main() -> anyhow::Result<()> {
    let cli = Cli::parse();

    let pool = SqlitePool::connect(&env::var("DATABASE_URL")?).await?;

    // todo!("make a command line option for this")
    Builder::new()
        .target(Target::Stdout)
        .parse_env("RUST_LOG")
        .init();


    match &cli.command {
        Some(Commands::Import { source_type, path }) => {
            println!("Importing {:?} from path: {}", source_type, path);

            let count = import(&pool, Path::new(path)).await?;
            println!("Imported {} epigrams", count);
        }
        Some(Commands::Context { openai }) => {
            let epigram_uuid = get_last_epigram(&pool).await?;

            let character = "-";
            let line_width = 80;
            let line = character.repeat(line_width);


            let epigram = get_epigram(&pool, &epigram_uuid).await?;
            display_epigram(&epigram, None);
            //let epigram = get_epigram(&pool, &epigram_uuid).await?;
            println!("{}\n\n{}\n", epigram.content.clone().unwrap(), line);
            let result = wait_with_spinner(context(&epigram)).await;
            match result {
                Ok(msg) => {
                    let formatted_chat = fill(&msg, line_width);
                    println!("{}", formatted_chat);
                }
                Err(e) => eprintln!("Error: {}", e),
            }
        }
        Some(Commands::Favorite {}) => {
            favorite(&pool).await;
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
                get_impression(&pool, Some(bucket)).await?;
            } else {
                get_impression(&pool, None).await?;
            }
        }
    }

    Ok(())
}

async fn get_impression(pool: &SqlitePool, bucket: Option<&String>) -> anyhow::Result<()> {
    // todo!("fix these runtime errors")
    // called `Result::unwrap()` on an `Err` value: error occurred while decoding column 0: invalid utf-8 sequence of 1 bytes from index 1
    let (epigram_uuid, bucket_name) = get_random_epigram(&pool, bucket).await.unwrap();

    let epigram = get_epigram(&pool, &epigram_uuid).await?;
    display_epigram(&epigram, Some(bucket_name));

    post_impression(pool, &epigram_uuid, epigram.bucket_id.unwrap()).await.expect("Error posting impression");

    Ok(())
}

fn display_epigram(epigram: &Epigram, bucket_name: Option<String>) {
    debug!("{:?}", epigram.epigram_uuid);
    let output = format!(
        "\n{}\nBucket: {}\n",
        epigram.content.as_deref().unwrap_or("N/A"),
        &bucket_name.clone().unwrap_or_default()
    );

    // Single flush to stdout
    println!("{}", output);
}

async fn favorite(pool: &SqlitePool) {
    let result = save_last_epigram(&pool).await;

    match result {
        Ok(_) => {
            println!("Saved!")
        }
        Err(err) => {
            eprintln!("Failed to save last epigram! {:?}", err);
        }
    }
}

use dotenvy::dotenv;
use fim::models::Epigram;
use indicatif::{ProgressBar, ProgressStyle};
use openai::{
    chat::{ChatCompletion, ChatCompletionMessage, ChatCompletionMessageRole},
    set_key,
};
use std::env;
use std::sync::Arc;
use std::time::Duration;
use tokio::io::AsyncBufReadExt;
use tokio::sync::Notify;
use tokio::task;

async fn context(epigram: &Epigram) -> Result<String, Box<dyn std::error::Error>> {
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
    F: std::future::Future<Output=R>,
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


async fn import(pool: &SqlitePool, directory: &Path) -> anyhow::Result<i32> {

    // Attempt to read the directory
    let mut entries = fs::read_dir(directory).await?; //.await.map_err(|_| "could not read files");
    let mut count: i32 = 0;

    while let Some(entry) = entries.next_entry().await? {
        //let entry = entry;
        let path = entry.path();

        // Only process files, not directories
        if path.is_file() {
            let bucket_name = path.file_stem().unwrap().to_str().unwrap().to_string();
            let bucket_id = lookup_or_add_bucket_by_name(&pool, &bucket_name).await.unwrap();

            debug!("Processing {:?}", path);
            if let Ok(file) = fs::File::open(&path).await {
                let mut reader = io::BufReader::new(file);
                let mut line = String::new();
                let mut fortune = String::new();

                loop {
                    let num_bytes = reader.read_line(&mut line).await?;
                    if num_bytes == 0 {
                        break;
                    }
                    //debug!("Reading from file - bytes {} - line {}", num_bytes, line);

                    if line == "%\n" {
                        if !fortune.is_empty() {
                            let epigram = fortune.trim();
                            debug!("Parsed Epigram:\n{}", epigram);
                            add_epigram(&pool, epigram.parse().unwrap(), bucket_id).await?;
                            fortune.clear();
                            line.clear();
                            count += 1;
                        }
                    } else {
                        fortune.push_str(&line);
                        line.clear();
                        //fortune.push('\n');
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