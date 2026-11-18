-- Identity concordance only; orders never prove administration.
WITH p AS (
 SELECT {keys},count(*) AS n FROM pharmacy
 WHERE {complete} GROUP BY {keys}
), ids AS (SELECT DISTINCT pharmacy_id FROM pharmacy WHERE pharmacy_id IS NOT NULL), x AS (
 SELECT CASE WHEN NOT ({rx_complete}) THEN 'missing_identity_key'
 WHEN p.n>1 THEN 'ambiguous_duplicate_key'
 WHEN p.n IS NULL AND ids.pharmacy_id IS NOT NULL THEN 'pharmacy_id_present_identity_discordant'
 WHEN p.n IS NULL THEN 'unmatched' ELSE 'unique_three_key_candidate' END AS state
 FROM prescriptions rx LEFT JOIN p ON {join}
 LEFT JOIN ids ON rx.pharmacy_id=ids.pharmacy_id
)
SELECT state,count(*) AS count FROM x GROUP BY state ORDER BY state;
