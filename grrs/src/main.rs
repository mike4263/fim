use clap::Parser;
use std::io::prelude::*;
use anyhow::{Context, Result};
use std::io::BufReader;
use std::fs::File;
use std::thread;
use std::time::Duration;
use log::{debug, info, warn};


#[derive(Parser, Debug)]
struct Cli {
    /// The pattern to look for
    pattern: String,
    /// The path to the file to read
    path: std::path::PathBuf,
}

fn main() -> Result<()> {
    let args = Cli::parse();
    env_logger::init();

    //let path = args.path.as_path().to_str().unwrap();

    let content = std::fs::read_to_string(&args.path)
        .with_context(|| format!("could not read file `{}`", args.path.display()))?;
    let pb = indicatif::ProgressBar::new(10);
    for i in 0..10 {
        let delay = Duration::from_millis(40);

        // Pause the current thread for 1 second
        thread::sleep(delay);

        //pb.println(format!("[+] finished #{}", i));
        pb.inc(1);
    }
    pb.finish_with_message("done");

    grrs::find_matches(&content, &args.pattern, &mut std::io::stdout());

    debug!("Finished processing messages");


    Ok(())
}




#[test]
fn check_answer_validity() {
    assert_eq!(answer(), 42);
}

fn answer() -> i32 {
    42
}


