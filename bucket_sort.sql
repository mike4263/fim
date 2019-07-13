create view total_counts as
select (total_impression_t.total_padded_impressions * 1.0) as total_padded_impressions,
       (total_epigram_t.total_epigrams * 1.0)        as total_epigrams,
       (total_weight_t.total_weighted_sum * 1.0)     as total_weighted_sum

from bucket b

         -- get the padded total impression count
         -- debug only??
         left outer join
     (select sum(t.impressions) as total_padded_impressions
      from (select b.bucket_id, (count(i.impression_id) + 1.0) as impressions
            from bucket b
                     left join impression i on b.bucket_id = i.bucket_id
            group by b.bucket_id
               --left join impression i on b.bucket_id = i.bucket_id group by b.bucket_id
           ) t
     ) total_impression_t

         -- get number of total epigrams
         left outer join
         (select count(e.epigram_uuid) as total_epigrams from epigram e) total_epigram_t


         left outer join
     (select sum(inner_e.weighted_epigram_count) as total_weighted_sum
      from (select e.bucket_id,
                   (count(1) * b2.item_weight) as weighted_epigram_count
            from epigram e
                     join bucket b2
            group by e.bucket_id) inner_e) total_weight_t
group by total_padded_impressions, total_epigrams, total_weighted_sum;



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




create view impressions_calculated as
       select calc.*, (expected_weighted_percentage + impression_delta) as effective_impression_percentage
           from
       (select bs.bucket_id, bs.name,
       (bs.epigram_weight / tc.total_weighted_sum) as expected_weighted_percentage,
       (bs.padded_impressions / tc.total_padded_impressions) as actual_impression_percentage,
       (bs.epigram_weight / tc.total_weighted_sum - bs.padded_impressions / tc.total_padded_impressions) as impression_delta
       --(bs.epigram_weight / tc.total_weighted_sum ) as view_modifier,
       --(bs.padded_impressions / tc.total_padded_impressions - bs.epigram_weight / tc.total_weighted_sum) as impression_delta2

       from bucket_sort bs
            left join total_counts tc ) calc

    where effective_impression_percentage > 0;
