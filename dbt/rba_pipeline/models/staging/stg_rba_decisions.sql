SELECT 
    PARSE_DATE('%e %B %Y', date) as date,
    SAFE_CAST(cash_rate AS NUMERIC) as cash_rate,
    SAFE_CAST(change AS NUMERIC) as rate_change
FROM
{{ source ('gold', 'rba_decisions')}}