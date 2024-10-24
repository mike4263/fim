pub mod models;

use rand::prelude::*;

use log::debug;

use crate::models::{BucketSort, Epigram};
use chrono::offset::Local;
use rand::distributions::Alphanumeric;
use rand::Rng;
use sqlx::sqlite::SqlitePool;
use sqlx::{Error, QueryBuilder, Sqlite};
use std::env;

pub async fn get_test_pool() -> anyhow::Result<SqlitePool> {
    //let database_url = dotenv!("DATABASE_URL");
    let pool = SqlitePool::connect(&env::var("DATABASE_URL")?).await?;
    //let pool = SqlitePool::connect(database_url).await?;
    Ok(pool)
}
pub async fn run_migrations(pool: &SqlitePool) -> anyhow::Result<()> {
    let result = sqlx::migrate!("db/migrations")
        .run(pool).await?;
    Ok(result)
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

pub async fn get_random_epigram(pool: &SqlitePool, bucket_name: Option<&String>) -> anyhow::Result<(String, String)> {
    let effective_bucket: BucketSort;
    if bucket_name.is_none() {
        effective_bucket = get_weighted_bucket(&pool).await?.unwrap_or_else(|| {
            BucketSort {
                bucket_id: 1,
                name: "".to_string(),
                epigram_count: 0.0,
                item_weight: 0,
            }
        });
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

                                         where
                                         --length(content) < ?1
                                         b.bucket_id = ?2
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
        bucket_id: rec.bucket_id,
        created_date: rec.created_date,
        modified_date: rec.modified_date,
        last_impression_date: rec.last_impression_date,
        content_source: rec.content_source,
        content_text: rec.content_text,
        content: rec.content,
        source_url: rec.source_url,
        action_url: rec.action_url,
        context_url: rec.context_url,
        gpt_completion: rec.gpt_completion,
        favorite: rec.favorite,
    };


    Ok(epigram_result)
}


#[tokio::test]
async fn test_epigram_and_save() {
    let pool = get_test_pool().await.expect("Error getting test pool");
    let results = get_random_epigram(&pool, None).await.unwrap();

    let epigram = get_epigram(&pool, &results.0).await.unwrap();

    post_impression(&pool, &results.0, epigram.bucket_id.unwrap()).await.expect("Failed to update impression");

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

pub async fn lookup_bucket_by_name(pool: &SqlitePool, bucket_name: &String) -> anyhow::Result<BucketSort> {
    let rec = sqlx::query!(
        r#"
select bs.bucket_id, bs.name, bs.epigram_count, bs.item_weight, bs.epigram_weight,
bs.padded_impressions from bucket_sort bs
where name = ?1
        "#, bucket_name
    ).fetch_one(pool).await;

    debug!("rec is {:?}", rec);

    match rec {
        Ok(rec) => {
            Ok(BucketSort {
                bucket_id: rec.bucket_id,
                name: rec.name.unwrap(),
                epigram_count: rec.epigram_count,
                item_weight: rec.item_weight.unwrap(),
            })
        }
        Err(e) => match e {
            Error::RowNotFound => {
                Err(e.into())
            }
            _ => panic!("Unable to query database: {}", e)
        }
    }
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
        epigram_count: rec.epigram_count,
        item_weight: rec.item_weight.unwrap(),
    };

    Ok(bucket_obj)
}


#[tokio::test]
async fn test_lookup_for_art() {
    let pool = get_test_pool().await.expect("Error getting test pool");

    let bucket1: String = String::from("art");
    let result: i64 = lookup_bucket_by_name(&pool, &bucket1).await.unwrap().bucket_id;
    assert_eq!(result, 1);

    let bucket2: String = String::from("food");
    let result: i64 = lookup_bucket_by_name(&pool, &bucket2).await.unwrap().bucket_id;
    assert_eq!(result, 11);
}


pub async fn post_impression(pool: &SqlitePool, last_epigram_uuid: &String, bucket_id: i64) -> anyhow::Result<()> {
    let impression_date_dt: String = Local::now().to_string();

    //epigram_obj.last_impression_date = Some(impression_date_dt.clone().to_string());
    let rows_affected = sqlx::query!(
        r#"
        update epigram set last_impression_date = ?1
        where epigram_uuid = ?2
        "#, impression_date_dt, last_epigram_uuid
    ).execute(pool).await?.rows_affected();
    debug!("Updated rows with impression date : {} ", rows_affected);

    let row_id = sqlx::query!(
        r#"
        insert into impression (bucket_id, epigram_uuid, impression_date)
values (?1, ?2, ?3)
        "#, bucket_id, last_epigram_uuid, impression_date_dt
    ).execute(pool).await?.last_insert_rowid();
    debug!("Inserted row id : {} ", row_id);

    Ok(())
}

pub async fn add_bucket(pool: &SqlitePool, bucket_name: &String) -> anyhow::Result<i64> {
    let row_id = sqlx::query!(
        r#"
        insert into bucket (name, item_weight)
values (?1, ?2)
        "#, bucket_name, 1
    ).execute(pool).await?.last_insert_rowid();
    debug!("Inserted row id : {} ", row_id);
    Ok(row_id)
}


fn generate_random_string(length: usize) -> String {
    let rng = thread_rng(); // Obtain a random number generator

    rng.sample_iter(&Alphanumeric)
        .take(length)
        .map(char::from)
        .collect()
}


pub async fn lookup_or_add_bucket_by_name(pool: &SqlitePool, bucket_name: &String) -> anyhow::Result<i64> {
    let find_bucket = lookup_bucket_by_name(&pool, &bucket_name).await;
    let mut bucket_id = find_bucket.unwrap_or_else(|e| {
        if let Some(sqlx::Error::RowNotFound) = e.downcast_ref::<sqlx::Error>() {
            return BucketSort {
                bucket_id: 0,
                name: "".to_string(),
                epigram_count: 0.0,
                item_weight: 0,
            };
        } else {
            panic!("error {:?}", e);
        }
    }).bucket_id;

    //todo!("is there a more idiomatic way to do this without creating a fake object")
    if bucket_id == 0 {
        bucket_id = add_bucket(&pool, &bucket_name).await.unwrap();
    }

    Ok(bucket_id)
}

#[tokio::test]
async fn test_add_bucket() {
    let pool = get_test_pool().await.expect("Error getting test pool");

    let bucket_name = String::from(generate_random_string(6));

    let bucket_id = lookup_or_add_bucket_by_name(&pool, &bucket_name).await.unwrap();

    let mut epigrams: Vec<EpigramInsert> = Vec::new();
    epigrams.push(EpigramInsert {
        epigram_uuid: Uuid::new_v4().to_string(),
        bucket_id: bucket_id,
        created_date: Local::now().to_string(),
        modified_date: Local::now().to_string(),
        content: String::from("hello world"),
    });

    add_epigrams(&pool, &epigrams)
        .await.unwrap();
}

pub struct EpigramInsert {
    pub epigram_uuid: String,
    pub bucket_id: i64,
    pub created_date: String,
    pub modified_date: String,
    pub content: String,
}

pub async fn add_epigrams(pool: &SqlitePool, epigrams: &Vec<EpigramInsert>) -> anyhow::Result<()> {
    let mut query_builder: QueryBuilder<Sqlite> = QueryBuilder::new(
        "insert into epigram (epigram_uuid, bucket_id, created_date, modified_date, content) "
    );

    query_builder.push_values(epigrams.iter(), |mut b, epigram| {
        b.push_bind(&epigram.epigram_uuid)
            .push_bind(epigram.bucket_id)
            .push_bind(&epigram.created_date)
            .push_bind(&epigram.modified_date)
            .push_bind(&epigram.content);
    });


    let query = query_builder.build();

    query.execute(pool).await?;

    Ok(())
}