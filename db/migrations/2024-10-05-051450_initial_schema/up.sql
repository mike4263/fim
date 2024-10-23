-- Your SQL goes here
CREATE TABLE `bucket`(
	`bucket_id` INTEGER NOT NULL PRIMARY KEY,
	`name` TEXT,
	`item_weight` INTEGER
);

CREATE TABLE `epigram`(
	`epigram_uuid` TEXT NOT NULL PRIMARY KEY,
	`bucket_id` INTEGER,
	`created_date` TEXT,
	`modified_date` TEXT,
	`last_impression_date` TEXT,
	`content_source` TEXT,
	`content_text` TEXT,
	`content` TEXT,
	`source_url` TEXT,
	`action_url` TEXT,
	`context_url` TEXT,
	`gpt_completion` TEXT,
	FOREIGN KEY (`bucket_id`) REFERENCES `bucket`(`epigram_uuid`)
);

CREATE TABLE `impression`(
	`impression_id` INTEGER NOT NULL PRIMARY KEY,
	`bucket_id` INTEGER,
	`epigram_uuid` TEXT,
	`impression_date` TEXT,
	`saved` BOOL,
	`gpt_completion` TEXT,
	FOREIGN KEY (`bucket_id`) REFERENCES `bucket`(`impression_id`),
	FOREIGN KEY (`epigram_uuid`) REFERENCES `epigram`(`impression_id`)
);

