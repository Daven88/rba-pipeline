SELECT *
FROM
{{ source('gold', 'stg_interest_rates_raw') }}