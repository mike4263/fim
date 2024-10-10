// @generated automatically by Diesel CLI.

diesel::table! {
    bucket (bucket_id) {
        bucket_id -> Integer,
        name -> Nullable<Text>,
        item_weight -> Nullable<Integer>,
    }
}

diesel::table! {
    bucket_sort (bucket_id) {
        bucket_id -> Integer,
        name -> Nullable<Text>,
        epigram_count -> Integer,
        item_weight -> Nullable<Integer>,
    }
}


diesel::table! {
    epigram (epigram_uuid) {
        epigram_uuid -> Text,
        bucket_id -> Nullable<Integer>,
        created_date -> Nullable<Text>,
        modified_date -> Nullable<Text>,
        last_impression_date -> Nullable<Text>,
        content_source -> Nullable<Text>,
        content_text -> Nullable<Text>,
        content -> Nullable<Text>,
        source_url -> Nullable<Text>,
        action_url -> Nullable<Text>,
        context_url -> Nullable<Text>,
        gpt_completion -> Nullable<Text>,
    }
}

diesel::table! {
    impression (impression_id) {
        impression_id -> Integer,
        bucket_id -> Nullable<Integer>,
        epigram_uuid -> Nullable<Text>,
        impression_date -> Nullable<Text>,
        saved -> Nullable<Bool>,
        gpt_completion -> Nullable<Text>,
    }
}

diesel::joinable!(epigram -> bucket (bucket_id));
diesel::joinable!(impression -> bucket (bucket_id));
diesel::joinable!(impression -> epigram (epigram_uuid));

diesel::allow_tables_to_appear_in_same_query!(
    bucket,
    epigram,
    impression,
);
