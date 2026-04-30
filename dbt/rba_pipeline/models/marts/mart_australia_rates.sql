SELECT DISTINCT *
FROM {{ ref('stg_interest_rates') }}
WHERE country_name = 'Australia'
AND value IS NOT NULL

