-- Identity linkage partitions among timestamp-eligible invented records only.
WITH visible_parents AS (
    SELECT subject_id, emar_id, emar_seq, count(*) AS parent_count
    FROM emar
    WHERE event_time IS NOT NULL
      AND available_time IS NOT NULL
      AND event_time <= CAST(? AS TIMESTAMP)
      AND available_time <= CAST(? AS TIMESTAMP)
    GROUP BY subject_id, emar_id, emar_seq
), visible_details AS (
    SELECT d.*
    FROM details d
    WHERE d.event_time IS NOT NULL
      AND d.available_time IS NOT NULL
      AND d.event_time <= CAST(? AS TIMESTAMP)
      AND d.available_time <= CAST(? AS TIMESTAMP)
), classified AS (
    SELECT d.row_id,
           CASE
               WHEN d.subject_id IS NULL OR d.emar_id IS NULL
                    OR d.emar_seq IS NULL THEN 'MISSING_KEY'
               WHEN p.parent_count IS NULL THEN 'UNMATCHED_PARENT'
               WHEN p.parent_count > 1 THEN 'AMBIGUOUS_PARENT'
               ELSE 'UNIQUE_PARENT_LINK'
           END AS linkage_state
    FROM visible_details d
    LEFT JOIN visible_parents p
      ON d.subject_id = p.subject_id
     AND d.emar_id = p.emar_id
     AND d.emar_seq = p.emar_seq
), states(linkage_state) AS (
    VALUES ('MISSING_KEY'), ('UNMATCHED_PARENT'),
           ('AMBIGUOUS_PARENT'), ('UNIQUE_PARENT_LINK')
)
SELECT s.linkage_state, count(c.row_id)::BIGINT AS detail_rows
FROM states s
LEFT JOIN classified c USING (linkage_state)
GROUP BY s.linkage_state
ORDER BY s.linkage_state;
