create view bucket_sort as
select b.bucket_id,
       b.name,

       -- these are just for debugging purposes
       (weights_epigramn_t.regular_epigram_count * 1.0)               as epigram_count,
       b.item_weight,
       IFNULL((weights_epigramn_t.weighted_epigram_count * 1.0), 0.0) as epigram_weight,

       padded_impressions_t.real_impressions,
       (padded_impressions_t.padded_impressions * 1.0)                as padded_impressions


from bucket b

      --  multiple the number of epigrams per bucket by its item weight
     left outer join

     (
       select e.bucket_id, count(1) as regular_epigram_count,
              (count(1) * b2.item_weight) as weighted_epigram_count

       from epigram e
          join bucket b2
               on e.bucket_id = b2.bucket_id
          group by e.bucket_id) weights_epigramn_t
            on b.bucket_id = weights_epigramn_t.bucket_id


         --  determine the number of impresssions of each bucket (+1 to accomdoate any buckets w\o impressions)
         left outer join
     (
         select b.bucket_id,
                IFNULL(count(i.bucket_id), 0.0) as real_impressions,
                (count(i.bucket_id) + 1.0)      as padded_impressions
         from bucket b
                  left join impression i on b.bucket_id = i.bucket_id
         group by b.bucket_id
     ) padded_impressions_t
     on b.bucket_id = padded_impressions_t.bucket_id

left join total_counts tc;