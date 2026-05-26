SELECT 
    PARSE_DATE('%e %B %Y', date) AS date,
    cash_rate,
    change as rate_change
FROM
{{ source ('gold', 'rba_decisions')}}