use fim::{add_epigrams, get_epigram, get_last_epigram, get_random_epigram, lookup_or_add_bucket_by_name, post_impression, run_migrations, save_last_epigram, EpigramInsert};
use std::collections::VecDeque;

use clap::{Parser, Subcommand};
use env_logger::{Builder, Target};
use log::debug;
use std::path::{Path, PathBuf};
use textwrap::fill;
use tokio::io;
use tokio::{fs, stream};

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

    let fim_db = &env::var("FIM_DB_URL")?.to_string();
    OpenOptions::new().create(true).write(true).open(fim_db).await?;

    let fim_db_prefix = "sqlite://";
    let results = format!("{}{}", fim_db_prefix, fim_db);

    println!("Opening DB {}", results);

    let pool = SqlitePool::connect(&results).await?;

    // todo!("make a command line option for this")
    Builder::new()
        .target(Target::Stdout)
        .parse_env("RUST_LOG")
        .init();


    match &cli.command {
        Some(Commands::Import { source_type, path }) => {
            println!("Configuring database");
            let _ = run_migrations(&pool).await?;

            println!("Importing {:?} from path: {}", source_type, path);

            //let count = import(&pool, Path::new(path)).await?;
            let pool_clone = Arc::new(pool);
            let count = wait_with_spinner(import(pool_clone.clone(), Path::new(path)), String::from("Importing fortune...")).await?;
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
            let result = wait_with_spinner(context(&epigram), String::from("Asking ChatGPT...")).await;
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
            let results = run_migrations(&pool).await?;
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
    // called `Result::unwrap()` on an `Err` value: no rows returned by a query that expected to return at least one row
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

use chrono::Local;
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
use tokio::fs::OpenOptions;
use tokio::io::AsyncBufReadExt;
use tokio::sync::{mpsc, Mutex, Notify};
use tokio::task;
use uuid::Uuid;

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


async fn wait_with_spinner<F, R>(async_op: F, message: String) -> R
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
                "▹ ▹ ▹ ▹ ▹ ",
                "▸ ▹ ▹ ▹ ▹ ",
                "▹ ▸ ▹ ▹ ▹ ",
                "▹ ▹ ▸ ▹ ▹ ",
                "▹ ▹ ▹ ▸ ▹ ",
                "▹ ▹ ▹ ▹ ▸ ",
                "▪ ▪ ▪ ▪ ▪ ",
            ]),
    );
    pb.set_message(message);

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

use futures::stream::{FuturesUnordered, StreamExt};
use tokio::sync::mpsc::Sender;

async fn import(pool: Arc<SqlitePool>, directory: &Path) -> anyhow::Result<i32> {

    // Attempt to read the directory
    let mut entries = fs::read_dir(directory).await?; //.await.map_err(|_| "could not read files");
    let mut count: i32 = 0;

    let mut task_queue: Vec<(PathBuf, i64)> = Vec::new();
    let tasks = FuturesUnordered::new();
    let (tx, mut rx) = mpsc::channel(100_000);


    while let Some(entry) = entries.next_entry().await? {
        //let entry = entry;
        let path = entry.path();

        // Only process files, not directories
        if path.is_file() {
            let bucket_name = path.file_stem().unwrap().to_str().unwrap().to_string();
            let bucket_id = lookup_or_add_bucket_by_name(&pool, &bucket_name).await?;

            task_queue.push((path, bucket_id));
        }
    }

    let _ = task_queue.iter().for_each(|(path, bucket_id)| {
        tasks.push(import_bucket(path, bucket_id, tx.clone()));
    });

    drop(tx);


    let future = task::spawn(async move {
        // Batch processor task
        let mut buffer = Vec::new();

        while let Some(item) = rx.recv().await {
            buffer.push(item);
            if buffer.len() >= 1000 {
                add_epigrams(&pool, &buffer).await.unwrap();
                //insert_batch(&db_pool, &buffer).await?;
                buffer.clear();
            }
        }

        // Insert any remaining items that didn't complete a full batch
        if !buffer.is_empty() {
            add_epigrams(&pool, &buffer).await.unwrap();
            //insert_batch(&db_pool, &buffer).await?;
        }
    });

    // todo!("get count")
    tasks.for_each(|result| async move {
        count = count + result.unwrap();
        debug!("Completed task!");
    }).await;


    //add_epigrams(&pool, Arc::clone(&epigrams_arc)).await?;
    future.await?;

    Ok(count)
}

async fn import_bucket(path: &PathBuf, bucket_id: &i64, tx: Sender<EpigramInsert>) -> anyhow::Result<i32> {
    let mut count: i32 = 0;
    //let mut epigrams: Vec<EpigramInsert> = Vec::new();
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
                    {
                        //let mut epigrams = tx.lock().await;
                        tx.send(EpigramInsert {
                            epigram_uuid: Uuid::new_v4().to_string(),
                            bucket_id: *bucket_id,
                            created_date: Local::now().to_string(),
                            modified_date: Local::now().to_string(),
                            content: epigram.parse()?,
                        }).await?;
                    }
                    //add_epigram(&pool, epigram.parse().unwrap(), bucket_id).await?;
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
    }
    //add_epigrams(&pool, epigrams).await?;
    drop(tx);
    Ok(count)
}