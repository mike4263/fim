use assert_cmd::prelude::*;
// Add methods on commands
use predicates::prelude::*;
// Used for writing assertions
use std::process::Command;
// Run programs

use lazy_static::lazy_static;
use std::sync::Once;

lazy_static! {
    static ref INIT: Once = Once::new();
}

fn initialize() {
    // Initialization code here, e.g., creating files or setting up a database.
    println!("Running setup code");
}


#[test]
fn file_doesnt_exist() -> Result<(), Box<dyn std::error::Error>> {
    INIT.call_once(|| initialize());

    let mut cmd = Command::cargo_bin("fim")?;

    cmd.arg("import").arg("fortune").arg("test_data/file/doesnt/exist");
    cmd.assert()
        .failure()
        .stderr(predicate::str::contains("Imported error: could not read files\n"));

    Ok(())
}
#[test]
fn file_import_100pack() -> Result<(), Box<dyn std::error::Error>> {
    INIT.call_once(|| initialize());

    let mut cmd = Command::cargo_bin("fim")?;

    cmd.arg("import").arg("fortune").arg("test_data/100pack");
    cmd.assert()
        .success()
        .stdout(predicate::str::contains("Imported 100 epigrams"));

    Ok(())
}