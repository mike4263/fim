create view total_counts as
select (total_impression_t.total_padded_impressions * 1.0) as total_padded_impressions,
       (total_epigram_t.total_epigrams * 1.0)              as total_epigrams,
       (total_weight_t.total_weighted_sum * 1.0)           as total_weighted_sum

from bucket b
         left outer join
     (select sum(t.impressions) as total_padded_impressions
      from (select b.bucket_id, (count(i.impression_id) + 1.0) as impressions
            from bucket b
                     left join impression i on b.bucket_id = i.bucket_id
            group by b.bucket_id
           ) t
     ) total_impression_t

         left outer join
         (select count(e.epigram_uuid) as total_epigrams from epigram e) total_epigram_t


         left outer join
     (select sum(inner_e.weighted_epigram_count) as total_weighted_sum
      from (select e.bucket_id,
                   (count(1) * b2.item_weight) as weighted_epigram_count
            from epigram e
                     join bucket b2
            on e.bucket_id = b2.bucket_id
            group by e.bucket_id) inner_e) total_weight_t
group by total_padded_impressions, total_epigrams, total_weighted_sum;