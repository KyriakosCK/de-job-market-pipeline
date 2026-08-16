select
    {{ surrogate_key('skill_name') }} as skill_id,
    skill_name,
    category,
    match_keyword
from {{ ref('skill_keywords') }}
