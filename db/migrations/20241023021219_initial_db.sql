--PRAGMA journal_mode = WAL;

--PRAGMA busy_timeout = milliseconds;

create table bucket
(
    bucket_id   INTEGER not null
        primary key,
    name        VARCHAR(50),
    item_weight INTEGER
);

-- auto-generated definition
create table epigram
(
    epigram_id           INTEGER not null primary key,
    epigram_uuid         VARCHAR not null,
    bucket_id            INTEGER
        references bucket,
    created_date         VARCHAR,
    modified_date        VARCHAR,
    last_impression_date VARCHAR,
    content_source       VARCHAR,
    content_text         VARCHAR,
    content              VARCHAR,
    source_url           VARCHAR,
    action_url           VARCHAR,
    context_url          VARCHAR,
    gpt_completion       VARCHAR,
    favorite             BOOLEAN default false
);



create table impression
(
    impression_id   INTEGER not null
        primary key,
    bucket_id       INTEGER
        references bucket,
    epigram_id      INTEGER
        references epigram,
    impression_date VARCHAR,
    saved           BOOLEAN,
    gpt_completion  VARCHAR
);