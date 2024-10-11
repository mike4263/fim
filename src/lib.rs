pub mod models;
pub mod schema;

use diesel::prelude::*;

use diesel::sql_query;
use diesel::sql_types::{Integer, Double};
use rand::prelude::*;

use log::debug;

use dotenvy::dotenv;
use std::env;
use diesel::dsl::sql;
use diesel::sql_types::Bool;
use rand::Rng;
use crate::models::{Bucket, BucketSort, Epigram, Impression};
use crate::schema::bucket::dsl::bucket;
use crate::schema::bucket_sort::dsl::bucket_sort;
use crate::schema::epigram::dsl::epigram;
use crate::schema::epigram::{favorite, last_impression_date};

use chrono::offset::Local; // Import to get the local time
use chrono::DateTime;

pub fn establish_connection() -> SqliteConnection {
    dotenv().ok();

    let database_url = env::var("DATABASE_URL").expect("DATABASE_URL must be set");
    SqliteConnection::establish(&database_url)
        .unwrap_or_else(|_| panic!("Error connecting to {}", database_url))
}



diesel::table! {
    impressions_calculated (bucket_id) {
        bucket_id -> Integer,
        name -> Text,
        effective_impression_percentage -> Double,
        impression_delta -> Double,
    }
}



// Assuming you have a database connection set up, replace `PgConnection` with the appropriate connection type
fn get_weighted_bucket() -> Option<BucketSort> {
    #[derive(QueryableByName)]
    struct Row {
        #[diesel(sql_type = Integer)]
        bucket_id: i32,
        #[diesel(sql_type = Double)]
        effective_impression_percentage: f64,
    }

    let mut conn = establish_connection();

    // Execute the SQL query
    let results = sql_query(
        "SELECT bucket_id, effective_impression_percentage FROM impressions_calculated WHERE impression_delta >= 0"
    )
        .load::<Row>(& mut conn)
        .expect("Failed to load data");

    let mut buckets = Vec::new();
    let mut probabilities = Vec::new();

    for row in results {
        buckets.push(row.bucket_id);
        probabilities.push(row.effective_impression_percentage);
    }

    // Use the rand crate to choose a bucket based on the weights
    if !buckets.is_empty() {
        let weighted_index = random_weighted_index(&probabilities);

        Some(lookup_bucket_by_id(&buckets[weighted_index]))
        //Some(buckets[weighted_index])
    } else {
        None
    }
}

fn random_weighted_index(weights: &[f64]) -> usize {
    let total_weight: f64 = weights.iter().sum();
    let mut rng = thread_rng();
    let mut random_weight: f64 = rng.gen_range(0.0..total_weight);
    for (index, &weight) in weights.iter().enumerate() {
        if random_weight < weight {
            return index;
        }
        random_weight -= weight;
    }
    weights.len() - 1 // fallback in edge cases
}






#[derive(Debug)]
pub struct CustomError(String);


pub fn get_epigram(bucket_name : Option<&String>) -> Result<(Epigram, Bucket), CustomError> {
    let connection = &mut establish_connection();

    let effective_bucket :BucketSort ;
    if bucket_name.is_none() {
        effective_bucket = get_weighted_bucket().unwrap();
    }
    else {
        effective_bucket = lookup_bucket(bucket_name.unwrap());
    }

    let mut rng = rand::thread_rng();

    let random_number: u32 = rng.gen_range(1..=effective_bucket.epigram_count) as u32 - 1;

    debug!("Effective bucket is {:?}", effective_bucket);

    let post = epigram
        .inner_join(bucket)
        .filter(crate::schema::bucket::columns::bucket_id.eq(effective_bucket.bucket_id))
        // todo!("this is hard coded in the view now")
        .filter(sql::<Bool>("LENGTH(content) < 300"))
        .limit(300)
        .select((epigram::all_columns(), bucket::all_columns()))
        .order_by(last_impression_date.asc())
        .offset(random_number as i64)
        .first::<(Epigram, Bucket)>(connection)
        .map_err(|err| CustomError(format!("Error loading posts offsetting {} : {} ",
                                           random_number, err))); // todo!("implement bucket in error output")

    post
}

#[test]
fn test_epigram_and_save() {
    let mut results = get_epigram(None).unwrap();
    post_impression(&mut results.0);
    let saved_result : Epigram = save_last_epigram().unwrap();
    assert_eq!(results.0.epigram_uuid, saved_result.epigram_uuid);
    //assert!(saved_result.favorite);
}


pub fn get_last_epigram() -> Result<Epigram, CustomError> {
    let connection = &mut establish_connection();

    let last_epigram = epigram
        .select(epigram::all_columns())
        .order_by(last_impression_date.desc())
        .first::<Epigram>(connection)
        .map_err(|err| CustomError(format!("Error loading posts : {} ", err)));

    last_epigram
}
pub fn save_last_epigram() -> Result<Epigram, CustomError> {

    let connection = &mut establish_connection();

    let last_epigram = get_last_epigram();

    if let Ok(ref last_epigram2) = last_epigram {
        diesel::update(epigram.find(last_epigram2.epigram_uuid.clone()))
            .set(favorite.eq(true))
            .execute(connection)
            .expect("Error updating last impression date");
    }

    last_epigram
}

fn lookup_bucket(bucket_name: &str) -> BucketSort {
    let connection = &mut establish_connection();

    let bucket_obj = bucket_sort
        .filter(crate::schema::bucket_sort::columns::name.eq(bucket_name))
        .select(bucket_sort::all_columns())
        .first::<BucketSort>(connection)
        .expect("Error loading posts");

    bucket_obj
}
fn lookup_bucket_by_id(bucket_id: &i32) -> BucketSort {
    let connection = &mut establish_connection();

    let bucket_obj = bucket_sort
        .filter(crate::schema::bucket_sort::columns::bucket_id.eq(bucket_id))
        .select(bucket_sort::all_columns())
        .first::<BucketSort>(connection)
        .expect("Error loading posts");

    bucket_obj
}
#[test]
fn test_lookup_for_art() {
    let result : i32 = lookup_bucket("art").bucket_id;
    assert_eq!(result, 1);

    let result : i32 = lookup_bucket("food").bucket_id;
    assert_eq!(result, 11);
}

pub fn post_impression(epigram_obj: &mut crate::models::Epigram)  {
    let connection = &mut establish_connection();

    let impression_date_dt : DateTime<Local> = Local::now();

    epigram_obj.last_impression_date = Some(impression_date_dt.clone().to_string());

    diesel::update(epigram.find(epigram_obj.epigram_uuid.clone()))
        .set(last_impression_date.eq(impression_date_dt.clone().to_string() ))
        .execute(connection)
        .expect("Error updating last impression date");

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
