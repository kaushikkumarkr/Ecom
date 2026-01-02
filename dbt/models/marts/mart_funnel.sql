with sessions as (

    select * from {{ ref('fct_sessions') }}

)

select
    -- Dimesion
    traffic_source,
    
    -- Funnel Steps (Aggregated)
    count(distinct session_id) as total_sessions,
    sum(has_product_view) as sessions_with_view,
    sum(has_add_to_cart) as sessions_with_cart,
    sum(has_purchase) as sessions_with_purchase,
    
    -- Conversion Rates (Calculated in BI usually, but good to have pre-calculated too)
    sum(has_product_view) * 1.0 / count(distinct session_id) as view_rate,
    sum(has_add_to_cart) * 1.0 / nullif(sum(has_product_view),0) as cart_add_rate,
    sum(has_purchase) * 1.0 / nullif(sum(has_add_to_cart),0) as purchase_rate,
    sum(has_purchase) * 1.0 / count(distinct session_id) as session_conversion_rate

from sessions
group by 1
order by 1
