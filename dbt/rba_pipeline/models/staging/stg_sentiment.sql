SELECT
    DATE_ADD(CAST(src.date AS DATE), INTERVAL 1 DAY) AS decision_date,
    src.sentiment,
    src.confidence,
    src.dominant_concern,
    src.reasoning
FROM
{{ source ('rba_minutes', 'sentiment')}} AS src
