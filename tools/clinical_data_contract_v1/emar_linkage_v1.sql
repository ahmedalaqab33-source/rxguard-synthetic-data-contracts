-- Full parent identity, no admission borrowing, no clinical/status interpretation.
WITH valid_parents AS (
 SELECT subject_id, emar_id, emar_seq, count(*) AS parent_count
 FROM parents WHERE subject_id IS NOT NULL AND emar_id IS NOT NULL AND emar_seq IS NOT NULL
 GROUP BY subject_id,emar_id,emar_seq
), classified AS (
 SELECT d.row_id,d.subject_id,d.emar_id,d.emar_seq,
 CASE WHEN d.subject_id IS NULL OR d.emar_id IS NULL OR d.emar_seq IS NULL THEN 'MISSING_KEY'
      WHEN p.parent_count IS NULL THEN 'ORPHAN'
      WHEN p.parent_count>1 THEN 'AMBIGUOUS_PARENT'
      ELSE 'UNIQUE_PARENT_LINK' END AS linkage_state
 FROM details d LEFT JOIN valid_parents p
 ON d.subject_id=p.subject_id AND d.emar_id=p.emar_id AND d.emar_seq=p.emar_seq
), child_counts AS (
 SELECT subject_id,emar_id,emar_seq,count(*) AS children FROM classified
 WHERE linkage_state='UNIQUE_PARENT_LINK' GROUP BY subject_id,emar_id,emar_seq
)
SELECT 'parent_rows' AS metric,count(*)::BIGINT AS count FROM parents
UNION ALL SELECT 'parent_missing_key_rows',count(*) FROM parents WHERE subject_id IS NULL OR emar_id IS NULL OR emar_seq IS NULL
UNION ALL SELECT 'parent_duplicate_keys',count(*) FROM valid_parents WHERE parent_count>1
UNION ALL SELECT 'unique_parent_keys',count(*) FROM valid_parents WHERE parent_count=1
UNION ALL SELECT 'detail_rows',count(*) FROM details
UNION ALL SELECT 'classified_detail_rows',count(*) FROM classified
UNION ALL SELECT 'missing_key_detail_rows',count(*) FROM classified WHERE linkage_state='MISSING_KEY'
UNION ALL SELECT 'orphan_detail_rows',count(*) FROM classified WHERE linkage_state='ORPHAN'
UNION ALL SELECT 'ambiguous_parent_detail_rows',count(*) FROM classified WHERE linkage_state='AMBIGUOUS_PARENT'
UNION ALL SELECT 'unique_parent_link_detail_rows',count(*) FROM classified WHERE linkage_state='UNIQUE_PARENT_LINK'
UNION ALL SELECT 'unique_parents_without_detail',count(*) FROM valid_parents p
 LEFT JOIN child_counts c USING(subject_id,emar_id,emar_seq) WHERE p.parent_count=1 AND c.children IS NULL
UNION ALL SELECT 'max_details_per_unique_parent',coalesce(max(children),0) FROM child_counts
ORDER BY metric;
