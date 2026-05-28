{{ config(materialized='table') }}

SELECT
    rba.date,
    rba.rate_change,
    rba.cash_rate,
    feat.trimmed_mean_yoy,
    LAG(feat.trimmed_mean_yoy) OVER (ORDER BY rba.date) AS trimmed_mean_yoy_lag1,
    feat.unemployed__ AS unemployment_rate,
    LAG(feat.unemployed__) OVER (ORDER BY rba.date) AS unemployment_rate_lag1,
    feat.ratio_commodity,
    LAG(feat.ratio_commodity) OVER (ORDER BY rba.date) AS ratio_commodity_lag1,
    feat.GDP__ AS GDP_growth,
    LAG(feat.GDP__) OVER (ORDER BY rba.date) AS GDP_growth_lag1,
    feat.government_spending,
    LAG(feat.government_spending) OVER (ORDER BY rba.date) AS government_spending_lag1,
    feat.year_ended_productivity_growth,
    LAG(feat.year_ended_productivity_growth) OVER (ORDER BY rba.date) AS year_ended_productivity_growth_lag1
FROM {{ ref ('stg_rba_decisions') }} AS rba
JOIN {{ ref ('int_rba_features') }} AS feat
ON rba.date = feat.decision_date