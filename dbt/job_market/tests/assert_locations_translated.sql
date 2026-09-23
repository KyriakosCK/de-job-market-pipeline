-- Singular test: lists non-Latin-script locations that have no entry in
-- seeds/location_translations.csv. int_jobs_unioned shows those as
-- "Unspecified", so each row returned here is a translation to add to the
-- seed. Warn-only: nothing unreadable reaches the dashboard either way.
{{ config(severity='warn') }}

select distinct source_location
from {{ ref('int_jobs_unioned') }}
where location is null
  and {{ is_non_latin('source_location') }}
