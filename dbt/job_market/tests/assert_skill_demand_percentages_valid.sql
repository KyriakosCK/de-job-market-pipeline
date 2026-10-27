-- A skill's share must be within 0-100%; anything else means a broken join
-- or double-counted bridge rows.
select skill_id, pct_of_active_postings
from {{ ref('mart_skill_demand') }}
where pct_of_active_postings < 0
   or pct_of_active_postings > 100
