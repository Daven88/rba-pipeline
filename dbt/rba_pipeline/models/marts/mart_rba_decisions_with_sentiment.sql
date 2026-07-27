SELECT
    dec.*,
    sent.sentiment,
    sent.confidence,
    sent.dominant_concern,
    sent.reasoning
FROM {{ ref ('mart_rba_decisions') }} AS dec
LEFT JOIN {{ ref ('stg_sentiment') }} AS sent
ON dec.date = sent.decision_date
