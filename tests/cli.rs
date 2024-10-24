use assert_cmd::prelude::*;
// Add methods on commands
use predicates::prelude::*;
// Used for writing assertions
use std::process::Command;
use std::{fs, io};
// Run programs

use lazy_static::lazy_static;
use serial_test::serial;
use std::sync::Once;

lazy_static! {
    static ref INIT: Once = Once::new();
}

fn initialize() {
    // Initialization code here, e.g., creating files or setting up a database.
    println!("Running setup code");
    delete_file_if_exists("/app/fim-bench.db").unwrap();
}
fn delete_file_if_exists(file_path: &str) -> io::Result<()> {
    match fs::remove_file(file_path) {
        Ok(_) => {
            println!("File '{}' deleted successfully.", file_path);
            Ok(())
        }
        Err(ref e) if e.kind() == io::ErrorKind::NotFound => {
            // The file was not found, ignore the error
            println!("File '{}' does not exist, ignoring.", file_path);
            Ok(())
        }
        Err(e) => {
            // Any other error, propagate it
            Err(e)
        }
    }
}

#[test]
fn file_doesnt_exist() -> Result<(), Box<dyn std::error::Error>> {
    INIT.call_once(|| initialize());

    let mut cmd = Command::cargo_bin("fim")?;
    cmd.env("FIM_DB_URL", "/app/fim-bench.db");

    cmd.arg("import").arg("fortune").arg("test_data/file/doesnt/exist");
    cmd.assert()
        .failure()
        .stderr(predicate::str::contains("Error: No such file or directory (os error 2)\n"));

    Ok(())
}
#[test]
#[serial]
fn file_import_100pack() -> Result<(), Box<dyn std::error::Error>> {
    INIT.call_once(|| initialize());

    let mut cmd = Command::cargo_bin("fim")?;
    cmd.env("FIM_DB_URL", "/app/fim-bench.db");

    cmd.arg("import").arg("fortune").arg("test_data/100pack");
    cmd.assert()
        .success()
        .stdout(predicate::str::contains("Imported 100 epigrams"));

    Ok(())
}

#[test]
#[serial]
fn file_import_legacy_content() -> Result<(), Box<dyn std::error::Error>> {
    INIT.call_once(|| initialize());

    let mut cmd = Command::cargo_bin("fim")?;
    cmd.env("FIM_DB_URL", "/app/fim-bench.db");

    cmd.arg("import").arg("fortune").arg("content/legacy_fortune");
    cmd.assert()
        .success()
        .stdout(predicate::str::contains("Imported 15498 epigrams"));

    Ok(())
}
#[test]
#[serial]
fn file_get_100_impressions() -> Result<(), Box<dyn std::error::Error>> {
    INIT.call_once(|| initialize());

    let mut cmd = Command::cargo_bin("fim")?;
    cmd.env("FIM_DB_URL", "/app/fim-bench.db");

    for i in 0..100 {
        //cmd.arg("");
        cmd.assert().success();
    }

    cmd.arg("favorite");
    cmd.assert().success();

    Ok(())
}

#[test]
fn test_init() -> Result<(), Box<dyn std::error::Error>> {
    INIT.call_once(|| initialize());

    let mut cmd = Command::cargo_bin("fim")?;
    cmd.env("FIM_DB_URL", "/app/fim-init.db");

    cmd.arg("init");
    cmd.assert()
        .success()
        .stdout(predicate::str::contains("Imported 15498 epigrams"));

    Ok(())
}