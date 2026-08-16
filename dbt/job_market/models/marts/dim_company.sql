with companies as (

    select distinct company_name
    from {{ ref('int_jobs_unioned') }}
    where company_name is not null

)

select
    {{ surrogate_key('company_name') }} as company_id,
    company_name
from companies
