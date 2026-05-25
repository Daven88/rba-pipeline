WITH cpi_match_cte AS (
    SELECT 
        rba.date AS decision_date,
        cpi.*,
        ROW_NUMBER() OVER (PARTITION BY rba.date ORDER BY cpi.date DESC) AS rn
    FROM {{ ref ('stg_rba_decisions') }} AS rba
    JOIN {{ ref ('stg_cpi') }} AS cpi
    ON CAST(TIMESTAMP_MICROS(cpi.date) AS DATE) <= rba.date
), 

lf_match_cte AS (
    SELECT 
        rba.date AS decision_date,
        lf.*,
        ROW_NUMBER() OVER (PARTITION BY rba.date ORDER BY lf.date DESC) AS rn
    FROM {{ ref ('stg_rba_decisions') }} AS rba
    JOIN {{ ref ('stg_labour_force') }} AS lf
    ON CAST(TIMESTAMP_MICROS(lf.date) AS DATE) <= rba.date
), 

cp_match_cte AS (
    SELECT 
        rba.date AS decision_date,
        cp.*,
        ROW_NUMBER() OVER (PARTITION BY rba.date ORDER BY cp.date DESC) AS rn
    FROM {{ ref ('stg_rba_decisions') }} AS rba
    JOIN {{ ref ('stg_commodity_prices') }} AS cp
    ON CAST(TIMESTAMP_MICROS(cp.date) AS DATE) <= rba.date
), 

gdp_match_cte AS (
    SELECT 
        rba.date AS decision_date,
        gdp.*,
        ROW_NUMBER() OVER (PARTITION BY rba.date ORDER BY gdp.date DESC) AS rn
    FROM {{ ref ('stg_rba_decisions') }} AS rba
    JOIN {{ ref ('stg_gdp') }} as gdp
    ON CAST(TIMESTAMP_MICROS(gdp.date) AS DATE) <= rba.date
), 

ge_match_cte AS (
    SELECT 
        rba.date AS decision_date,
        ge.*,
        ROW_NUMBER() OVER (PARTITION BY rba.date ORDER BY ge.date DESC) AS rn
    FROM {{ ref ('stg_rba_decisions') }} AS rba
    JOIN {{ ref ('stg_government_expenditure') }} as ge
    ON CAST(TIMESTAMP_MICROS(ge.date) AS DATE) <= rba.date
),

prd_match_cte AS (
    SELECT 
        rba.date AS decision_date,
        prd.*,
        ROW_NUMBER() OVER (PARTITION BY rba.date ORDER BY prd.date DESC) AS rn
    FROM {{ ref ('stg_rba_decisions') }} AS rba
    JOIN {{ ref ('stg_productivity') }} AS prd
    ON CAST(TIMESTAMP_MICROS(prd.date) AS DATE) <= rba.date
)

SELECT
    cpi.decision_date,
    cpi.trimmed_mean_yoy,
    lf.unemployed__,
    cp.bulk_AU_ / cp.overall_AU_ AS ratio_commodity, 
    gdp.GDP__,
    ge.government_spending,
    prd.year_ended_productivity_growth
FROM cpi_match_cte AS cpi
LEFT JOIN lf_match_cte AS lf 
ON cpi.decision_date = lf.decision_date
LEFT JOIN cp_match_cte AS cp
ON cpi.decision_date = cp.decision_date
LEFT JOIN gdp_match_cte AS gdp
ON cpi.decision_date = gdp.decision_date
LEFT JOIN ge_match_cte AS ge
ON cpi.decision_date = ge.decision_date
LEFT JOIN prd_match_cte AS prd
ON cpi.decision_date = prd.decision_date 
WHERE cpi.rn = 1 
AND lf.rn = 1
AND cp.rn = 1
AND gdp.rn = 1
AND ge.rn = 1
AND prd.rn = 1


