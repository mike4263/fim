#![feature(test)]
extern crate test;

use assert_cmd::assert::OutputAssertExt;
use assert_cmd::cargo::CommandCargoExt;
use predicates::prelude::predicate;
use std::process::Command;
use std::{fs, io};
use test::Bencher;

// Sample function to benchmark
fn fibonacci(n: u64) -> u64 {
    match n {
        0 => 0,
        1 => 1,
        _ => fibonacci(n - 1) + fibonacci(n - 2),
    }
}

// Benchmark function
#[bench]
fn bench_fibonacci(b: &mut Bencher) {
    b.iter(|| {
        // Code to benchmark
        let n = test::black_box(20);  // Use black_box to prevent compiler optimizations
        fibonacci(n)
    });
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

#[bench]
fn bench_run_import_100pk(b: &mut Bencher) {
    b.iter(|| {
        let mut cmd = Command::cargo_bin("fim").unwrap();

        delete_file_if_exists("/app/fim-bench.db").unwrap();
        cmd.env("FIM_DB_URL", "/app/fim-bench.db");

        cmd.arg("import").arg("fortune").arg("content/legacy_fortune");
        cmd.assert()
            .success()
            .stdout(predicate::str::contains("Imported 15498 epigrams"));
    });
}