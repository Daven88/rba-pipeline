{{ config(materialized='table') }}

SELECT
    rba.date,
    rba.rate_change,
    rba.cash_rate,
    feat.trimmed_mean_yoy,
    feat.unemployed__ AS unemployment_rate,
    feat.ratio_commodity,
    feat.GDP__ AS GDP_growth,
    feat.government_spending,
    feat.year_ended_productivity_growth
FROM {{ ref ('stg_rba_decisions') }} AS rba
JOIN {{ ref ('int_rba_features') }} AS feat
ON rba.date = feat.decision_date