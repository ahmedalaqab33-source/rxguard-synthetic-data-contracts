-- Synthetic engineering checks only. No drug/delivery/clinical classification.
WITH key_counts AS (
 SELECT itemid, count(*) AS n FROM dictionary WHERE itemid IS NOT NULL GROUP BY itemid
), unique_dictionary AS (
 SELECT d.* FROM dictionary d JOIN key_counts k USING(itemid) WHERE k.n=1
)
SELECT e.row_id,
 CASE WHEN e.itemid IS NULL THEN 'MISSING_KEY'
      WHEN k.n IS NULL THEN 'UNMATCHED_KEY'
      WHEN k.n>1 THEN 'AMBIGUOUS_DICTIONARY_KEY'
      WHEN d.linksto IS NULL THEN 'UNKNOWN_LINKSTO'
      WHEN d.linksto<>'inputevents' THEN 'LINKSTO_MISMATCH'
      ELSE 'UNIQUE_INPUTEVENTS_LINK' END AS linkage_state,
 CASE WHEN k.n IS NULL OR k.n<>1 THEN 'NOT_ASSESSED'
      WHEN d.unitname IS NULL OR e.amountuom IS NULL THEN 'UNKNOWN'
      WHEN d.unitname=e.amountuom THEN 'LITERAL_MATCH' ELSE 'LITERAL_MISMATCH' END AS unit_state,
 CASE WHEN e.starttime IS NULL OR e.endtime IS NULL THEN 'UNKNOWN'
      WHEN e.endtime<e.starttime THEN 'REVERSED' ELSE 'NONREVERSED' END AS interval_state,
 CASE WHEN e.storetime IS NULL THEN 'UNKNOWN'
      WHEN e.storetime<=CAST(? AS TIMESTAMP) THEN 'AT_OR_BEFORE' ELSE 'AFTER' END AS availability_state,
 CASE WHEN e.statusdescription IS NULL THEN 'MISSING_UNINTERPRETED' ELSE 'PRESENT_UNINTERPRETED' END AS status_state
FROM events e LEFT JOIN key_counts k ON e.itemid=k.itemid
LEFT JOIN unique_dictionary d ON e.itemid=d.itemid ORDER BY e.row_id;
