SELECT *
FROM {{ ref ('stg_rba_decisions') }} AS rba
ASOF JOIN {{ ref ('stg_cpi') }} AS cpi
    MATCH_CONDITION (rba.date >= cpi.date)
ASOF JOIN {{ ref ('stg_commodity_prices') }} AS cp
    MATCH_CONDITION (rba.date >= cp.date)
ASOF JOIN {{ ref ('stg_gdp') }} AS gdp
    MATCH_CONDITION (rba.date >= gdp.date)
ASOF JOIN {{ ref ('stg_government_expenditure') }} as ge
    MATCH_CONDITION (rba.date >= ge.date)
ASOF JOIN {{ ref ('stg_labour_force') }} as lf
    MATCH_CONDITION (rba.date >= lf.date)
ASOF JOIN {{ ref ('stg_productivity' )}} as p
    MATCH_CONDITION (rba.date >= p.date)
