pub mod models;
pub mod schema;

use diesel::prelude::*;

use rand::prelude::*;

use log::debug;

use crate::models::{BucketSort, Epigram};
use dotenvy::dotenv;
use rand::Rng;
use std::env;

use chrono::offset::Local;
// Import to get the local time
use chrono::DateTime;
use sqlx::sqlite::SqlitePool;


pub async fn get_test_pool() -> anyhow::Result<SqlitePool> {
    let pool = SqlitePool::connect(&env::var("DATABASE_URL")?).await?;
    Ok(pool)
}
pub fn establish_connection() -> SqliteConnection {
    let database_url: String;

    dotenv().ok();
    database_url = env::var("DATABASE_URL").expect("DATABASE_URL must be set");

    SqliteConnection::establish(&database_url)
        .unwrap_or_else(|_| panic!("Error connecting to {}", database_url))
}


pub fn run_migrations() -> Result<(), Box<dyn std::error::Error + Send + Sync + 'static>> {
    Ok(())
}

// Assuming you have a database connection set up, replace `PgConnection` with the appropriate connection type
async fn get_weighted_bucket(pool: &SqlitePool) -> anyhow::Result<Option<BucketSort>> {
    let weighted_buckets = sqlx::query!(
        r#"
        SELECT bucket_id, effective_impression_percentage FROM impressions_calculated WHERE impression_delta >= 0
        "#
    ).fetch_all(pool).await?;

    debug!("Weighted Buckets are {:?}", weighted_buckets);

    let mut buckets: Vec<i64> = Vec::new();
    let mut probabilities: Vec<f64> = Vec::new();

    for row in weighted_buckets {
        buckets.push(row.bucket_id);
        probabilities.push(row.effective_impression_percentage.unwrap());
    }

    // Use the rand crate to choose a bucket based on the weights
    if !buckets.is_empty() {
        let weighted_index = random_weighted_index(&probabilities);

        Ok(Some(lookup_bucket_by_id(&pool, &buckets[weighted_index]).await?))
        //Some(buckets[weighted_index])
    } else {
        Ok(None)
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


pub async fn get_random_epigram(pool: &SqlitePool, bucket_name: Option<&String>) -> anyhow::Result<(String, String)> {
    let effective_bucket: BucketSort;
    if bucket_name.is_none() {
        effective_bucket = get_weighted_bucket(&pool).await?.unwrap();
    } else {
        effective_bucket = lookup_bucket_by_name(&pool, bucket_name.unwrap()).await?;
    }

    let mut rng = rand::thread_rng();

    let random_number: u32 = rng.gen_range(1f64..=effective_bucket.epigram_count) as u32 - 1;

    debug!("Effective bucket is {:?}", effective_bucket);

    let rec = sqlx::query!(
        r#"
select e.epigram_uuid, b.name as bucket_name from epigram e
                       inner join bucket b
                       on e.bucket_id = b.bucket_id

                                         where length(content) < ?1
                                         and b.bucket_id = ?2
order by last_impression_date asc
limit ?3
offset ?4
        "#, 300, effective_bucket.bucket_id, effective_bucket.epigram_count, random_number
    ).fetch_one(pool).await?;

    debug!("rec is {:?}", rec);

    Ok((rec.epigram_uuid, rec.bucket_name.unwrap()))
}

pub async fn get_epigram(pool: &SqlitePool, epigram_uuid: &String) -> anyhow::Result<Epigram> {
    let rec = sqlx::query!(
        r#"
select e.* from epigram e
         where e.epigram_uuid = ?1
        "#, epigram_uuid
    ).fetch_one(pool).await?;

    debug!("rec is {:?}", rec);

    let epigram_result = Epigram {
        epigram_uuid: rec.epigram_uuid,
        bucket_id: None,
        created_date: rec.created_date,
        modified_date: rec.modified_date,
        last_impression_date: None,
        content_source: None,
        content_text: None,
        content: rec.content,
        source_url: None,
        action_url: None,
        context_url: None,
        gpt_completion: None,
        favorite: None,
    };


    Ok(epigram_result)
}


#[tokio::test]
async fn test_epigram_and_save() {
    let pool = get_test_pool().await.expect("Error getting test pool");
    let mut results = get_random_epigram(&pool, None).await.unwrap();
    post_impression(&pool, &results.0).await.expect("Failed to update impression");

    save_last_epigram(&pool).await.expect("Error saving last epigram");
    //assert_eq!(results.0.epigram_uuid, saved_result.epigram_uuid);
    //assert!(saved_result.favorite)
}


pub async fn get_last_epigram(pool: &SqlitePool) -> anyhow::Result<String> {
    let rec = sqlx::query!(
        r#"
select e.epigram_uuid from epigram e
                       inner join bucket b
                       on e.bucket_id = b.bucket_id
order by last_impression_date desc
limit 1
        "#
    ).fetch_one(pool).await?;

    debug!("rec is {:?}", rec);

    Ok(rec.epigram_uuid)
}
pub async fn save_last_epigram(pool: &SqlitePool) -> anyhow::Result<()> {
    let last_epigram_uuid = get_last_epigram(&pool).await?;

    let rows_affected = sqlx::query!(
        r#"
        update epigram set favorite = 1
        where epigram_uuid = ?1
        "#, last_epigram_uuid
    ).execute(pool).await?.rows_affected();

    debug!("Updated rows : {} ", rows_affected);

    Ok(())
}

async fn lookup_bucket_by_name(pool: &SqlitePool, bucket_name: &String) -> anyhow::Result<BucketSort> {
    let rec = sqlx::query!(
        r#"
select bs.bucket_id, bs.name, bs.epigram_count, bs.item_weight, bs.epigram_weight,
bs.padded_impressions from bucket_sort bs
where name = ?1
        "#, bucket_name
    ).fetch_one(pool).await?;

    debug!("rec is {:?}", rec);

    let bucket_obj: BucketSort = BucketSort {
        bucket_id: rec.bucket_id,
        name: rec.name.unwrap(),
        epigram_count: rec.epigram_count.unwrap(),
        item_weight: rec.item_weight.unwrap(),
    };

    Ok(bucket_obj)
}

async fn lookup_bucket_by_id(pool: &SqlitePool, bucket_id: &i64) -> anyhow::Result<BucketSort> {
    let rec = sqlx::query!(
        r#"
select bs.bucket_id, bs.name, bs.epigram_count, bs.item_weight, bs.epigram_weight,
bs.padded_impressions from bucket_sort bs
where bucket_id = ?1

        "#, bucket_id
    ).fetch_one(pool).await?;

    debug!("rec is {:?}", rec);

    let bucket_obj: BucketSort = BucketSort {
        bucket_id: rec.bucket_id,
        name: rec.name.unwrap(),
        epigram_count: rec.epigram_count.unwrap(),
        item_weight: rec.item_weight.unwrap(),
    };

    Ok(bucket_obj)
}


/*#[test]
fn test_lookup_for_art() {
    let result: i32 = lookup_bucket_by_name("art")?.bucket_id;
    assert_eq!(result, 1);

    let result: i32 = lookup_bucket_by_name("food")?.bucket_id;
    assert_eq!(result, 11);
}*/


pub async fn post_impression(pool: &SqlitePool, epigram_obj: &String) -> anyhow::Result<()> {
    let connection = &mut establish_connection();

    let impression_date_dt: DateTime<Local> = Local::now();

    //epigram_obj.last_impression_date = Some(impression_date_dt.clone().to_string());

    /*
    diesel::update(epigram.find(epigram_obj.epigram_uuid.clone()))
        .set(last_impression_date.eq(impression_date_dt.clone().to_string()))
        .execute(connection)
        .expect("Error updating last impression date");

    let new_impression = Impression {
        bucket_id: Option::from(epigram_obj.bucket_id),
        epigram_uuid: Some(epigram_obj.epigram_uuid.clone()),
        impression_date: Some(impression_date_dt.to_string()),
        saved: None,
        gpt_completion: None,
    };


    diesel::insert_into(crate::schema::impression::table)
        .values(&new_impression)
        .execute(connection)
        .expect("Error saving impression");

     */
    Ok(())
}

pub fn add_epigram(epigram_str: String) -> Result<(), CustomError> {
    Ok(())
}