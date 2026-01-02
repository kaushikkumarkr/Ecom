with events as (

    select * from {{ ref('stg_events') }}

),

session_agg as (

    select
        session_id,
        user_id,
        min(created_at)::timestamp as session_start_at,
        max(created_at)::timestamp as session_end_at,
        count(*) as total_events,
        
        -- Funnel Flags
        max(case when event_type = 'product' then 1 else 0 end) as has_product_view,
        max(case when event_type = 'cart' then 1 else 0 end) as has_add_to_cart,
        max(case when event_type = 'purchase' then 1 else 0 end) as has_purchase,
        
        -- Dimensions
        max(traffic_source) as traffic_source,
        max(browser) as browser,
        max(city) as city,
        max(state) as state

    from events
    group by 1, 2

)

select 
    *,
    {{ dbt.datediff("session_start_at", "session_end_at", "second") }} as session_duration_seconds
from session_agg
