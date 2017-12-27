CREATE TABLE metadata (
  metadata_id INTEGER,
  attribute TEXT NOT NULL,
  value TEXT NOT NULL,
  last_updated INTEGER,
  CONSTRAINT metadata_PK PRIMARY KEY (metadata_id)
);

CREATE TABLE bucket (
  bucket_id INTEGER NOT NULL,
  name TEXT,
  item_weight INTEGER,
  CONSTRAINT bucket_pk PRIMARY KEY (bucket_id)
);

CREATE TABLE epigram (
  epigram_uuid TEXT NOT NULL,
  bucket_id INTEGER NOT NULL,
  created_date INTEGER,
  modified_date INTEGER,
  content_source TEXT,
  content_type TEXT, -- values: plain, asciicast, source
  content TEXT NOT NULL,
  source_url TEXT, -- where the content originated from, (i.e. intro blog post)
  action_url TEXT, -- used with content_type (i.e. asciicast overview)
  context_url TEXT, -- deep dive info link (i.e. github repo)
  CONSTRAINT epigram_pk PRIMARY KEY (epigram_uuid),
  CONSTRAINT epigram_bucket_FK FOREIGN KEY (bucket_id) REFERENCES bucket(bucket_id)
);

CREATE TABLE impression (
  impression_id INTEGER NOT NULL,
  bucket_id INTEGER NOT NULL,
  epigram_uuid TEXT NOT NULL,
  impression_date INTEGER NOT NULL,
  CONSTRAINT impression_pk PRIMARY KEY (impression_id),
  CONSTRAINT impression_bucket_FK FOREIGN KEY (bucket_id) REFERENCES bucket(bucket_id),
  CONSTRAINT impression_epigram_FK FOREIGN KEY (epigram_uuid) REFERENCES epigram(epigram_uuid)
);

