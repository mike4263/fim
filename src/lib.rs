pub mod models;
pub mod schema;

use diesel::prelude::*;
use dotenvy::dotenv;
use std::env;
use diesel::dsl::sql;
use diesel::sql_types::Bool;
use rand::Rng;
use crate::models::{Bucket, Epigram, Impression};
use crate::schema::bucket::dsl::bucket;
use crate::schema::epigram::dsl::epigram;
use crate::schema::epigram::last_impression_date;

use chrono::offset::Local; // Import to get the local time
use chrono::DateTime;      // For handling DateTime object

pub fn establish_connection() -> SqliteConnection {
    dotenv().ok();

    let database_url = env::var("DATABASE_URL").expect("DATABASE_URL must be set");
    SqliteConnection::establish(&database_url)
        .unwrap_or_else(|_| panic!("Error connecting to {}", database_url))
}


pub fn get_epigram() -> (Epigram,Bucket) {
    let connection = &mut establish_connection();

    let mut rng = rand::thread_rng();

    // Generate a random number in a range, for example, between 1 and 100
    let random_number: u32 = rng.gen_range(1..=100);

    let post = epigram
        .inner_join(bucket)
        .filter(crate::schema::bucket::columns::name.eq("linux"))
        .filter(sql::<Bool>("LENGTH(content) < 300"))
        .limit(300)
        .select((epigram::all_columns(), bucket::all_columns()))
        .order_by(last_impression_date.asc())
        .offset(random_number as i64)
        .first::<(Epigram, Bucket)>(connection)
        .expect("Error loading posts");

    post
}

pub fn post_impression(epigram_obj: &crate::models::Epigram)  {
    let connection = &mut establish_connection();

    let impression_date_dt : DateTime<Local> = Local::now();

    let new_impression = Impression{
        bucket_id: Option::from(epigram_obj.bucket_id),
        epigram_uuid: Some(epigram_obj.epigram_uuid.clone()),
        impression_date: Some(impression_date_dt.to_string()),
        saved: None,
        gpt_completion: None };


    diesel::insert_into(crate::schema::impression::table)
        .values(&new_impression)
        .execute(connection)
        .expect("Error saving impression");

}
