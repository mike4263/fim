use fim_rust::models::*;
use diesel::prelude::*;
use diesel::dsl::sql;
use diesel::sql_types::{Bool };
use rand::Rng;

use fim_rust::{establish_connection, get_epigram};
use fim_rust::schema::epigram::dsl::*;
use fim_rust::schema::bucket::dsl::{bucket, name as bucket_name_column};

fn main() {

    let post = get_epigram();
    println!("{}", post.0.epigram_uuid);
    println!("-----------");
    println!("{}", post.0.content.unwrap_or("N/A".parse().unwrap()));
    println!("{:#?}", post.1.name);
    //}
}

