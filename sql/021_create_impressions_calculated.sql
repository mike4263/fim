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

   ;