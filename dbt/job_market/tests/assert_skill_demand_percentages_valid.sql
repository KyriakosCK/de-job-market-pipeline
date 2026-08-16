-- Singular test: a skill's share of postings should never exceed 100%,
-- and should never be negative. Catches a broken join or double-counted
-- bridge rows long before it reaches the dashboard.
select skill_id, pct_of_active_postings
from {{ ref('mart_skill_demand') }}
where pct_of_active_postings < 0
   or pct_of_active_postings > 100
