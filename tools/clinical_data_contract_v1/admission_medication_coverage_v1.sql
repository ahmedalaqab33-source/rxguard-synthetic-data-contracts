-- Invented-data coverage counts only; no drug exposure or clinical outcomes.
WITH eligible_orders AS (
    SELECT o.subject_id, o.hadm_id, o.source
    FROM orders o
    JOIN admissions a USING (subject_id, hadm_id)
    WHERE o.event_time IS NOT NULL
      AND o.available_time IS NOT NULL
      AND o.event_time <= a.index_time
      AND o.available_time <= a.index_time
), order_counts AS (
    SELECT subject_id, hadm_id,
           count(*) FILTER (WHERE source = 'PRESCRIPTION')::BIGINT
               AS prescription_order_evidence_rows,
           count(*) FILTER (WHERE source = 'PHARMACY')::BIGINT
               AS pharmacy_order_evidence_rows
    FROM eligible_orders
    GROUP BY subject_id, hadm_id
), eligible_emar AS (
    SELECT e.*
    FROM emar e
    JOIN admissions a USING (subject_id, hadm_id)
    WHERE e.event_time IS NOT NULL
      AND e.available_time IS NOT NULL
      AND e.event_time <= a.index_time
      AND e.available_time <= a.index_time
), emar_counts AS (
    SELECT subject_id, hadm_id,
           count(*)::BIGINT AS emar_record_rows,
           count(*)::BIGINT AS administration_status_unknown_emar_rows,
           count(*) FILTER (
               WHERE status_text IS NULL OR trim(status_text) = ''
           )::BIGINT AS emar_status_missing_rows,
           count(*) FILTER (
               WHERE status_text IS NOT NULL AND trim(status_text) <> ''
           )::BIGINT AS emar_status_present_uninterpreted_rows
    FROM eligible_emar
    GROUP BY subject_id, hadm_id
), eligible_parent_candidates AS (
    SELECT a.subject_id, a.hadm_id, a.index_time,
           e.emar_id, e.emar_seq,
           (
               SELECT count(*)
               FROM emar e2
               WHERE e2.subject_id = e.subject_id
                 AND e2.emar_id = e.emar_id
                 AND e2.emar_seq = e.emar_seq
                 AND e2.event_time IS NOT NULL
                 AND e2.available_time IS NOT NULL
                 AND e2.event_time <= a.index_time
                 AND e2.available_time <= a.index_time
           ) AS visible_parent_count
    FROM admissions a
    JOIN emar e
      ON e.subject_id = a.subject_id
     AND e.hadm_id = a.hadm_id
    WHERE e.emar_id IS NOT NULL
      AND e.emar_seq IS NOT NULL
      AND e.event_time IS NOT NULL
      AND e.available_time IS NOT NULL
      AND e.event_time <= a.index_time
      AND e.available_time <= a.index_time
), linked_details AS (
    SELECT d.row_id, p.subject_id, p.hadm_id
    FROM eligible_parent_candidates p
    JOIN details d
      ON d.subject_id = p.subject_id
     AND d.emar_id = p.emar_id
     AND d.emar_seq = p.emar_seq
    WHERE p.visible_parent_count = 1
      AND d.event_time IS NOT NULL
      AND d.available_time IS NOT NULL
      AND d.event_time <= p.index_time
      AND d.available_time <= p.index_time
), detail_counts AS (
    SELECT subject_id, hadm_id,
           count(*)::BIGINT AS linked_administration_detail_evidence_rows
    FROM linked_details
    GROUP BY subject_id, hadm_id
)
SELECT a.subject_id, a.hadm_id, a.index_time,
       coalesce(o.prescription_order_evidence_rows, 0)::BIGINT
           AS prescription_order_evidence_rows,
       coalesce(o.pharmacy_order_evidence_rows, 0)::BIGINT
           AS pharmacy_order_evidence_rows,
       coalesce(e.emar_record_rows, 0)::BIGINT AS emar_record_rows,
       coalesce(e.administration_status_unknown_emar_rows, 0)::BIGINT
           AS administration_status_unknown_emar_rows,
       coalesce(e.emar_status_missing_rows, 0)::BIGINT
           AS emar_status_missing_rows,
       coalesce(e.emar_status_present_uninterpreted_rows, 0)::BIGINT
           AS emar_status_present_uninterpreted_rows,
       coalesce(d.linked_administration_detail_evidence_rows, 0)::BIGINT
           AS linked_administration_detail_evidence_rows
FROM admissions a
LEFT JOIN order_counts o USING (subject_id, hadm_id)
LEFT JOIN emar_counts e USING (subject_id, hadm_id)
LEFT JOIN detail_counts d USING (subject_id, hadm_id)
ORDER BY a.hadm_id, a.subject_id;
