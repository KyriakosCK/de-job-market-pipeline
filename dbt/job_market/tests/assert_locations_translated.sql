-- Non-Latin locations missing from seeds/location_translations.csv (shown
-- as "Unspecified"). Each row is a translation to add.
{{ config(severity='warn') }}

select distinct source_location
from {{ ref('int_jobs_unioned') }}
where location is null
  and {{ is_non_latin('source_location') }}
