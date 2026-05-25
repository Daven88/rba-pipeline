SELECT 
    CAST(date AS DATE) AS date,
    cash_rate
FROM
{{ source ('gold', 'rba_decisions')}}