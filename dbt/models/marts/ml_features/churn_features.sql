-- Logic:
-- 1. Snapshot Date: '2023-09-01' (Same as Labels).
-- 2. Observation Window: 60 Days (2023-07-03 to 2023-09-01).
-- 3. Features: Only data FROM strictly BEFORE snapshot_date.

with parameters as (
    select '2023-09-01'::timestamp as snapshot_date
),

base_orders as (
    select *
    from {{ ref('stg_orders') }}
    cross join parameters p
    where created_at < p.snapshot_date
      and status not in ('Returned', 'Cancelled')
),

base_events as (
    select *
    from {{ ref('stg_events') }}
    cross join parameters p
    where created_at < p.snapshot_date
),

users as (
    select * from {{ ref('stg_users') }}
),

rfm as (
    select
        user_id,
        count(distinct order_id) as frequency_all_time,
        sum(1) as monetary_proxy, -- Using count as proxy if items heavy, ideally sum(sale_price)
        max(created_at) as last_order_date,
        min(created_at) as first_order_date
    from base_orders
    group by 1
),

windowed_rfm as (
    -- Strict 60 Day Window Features
    select
        user_id,
        count(distinct order_id) as frequency_60d,
        count(distinct case when created_at >= (p.snapshot_date - interval '30 days') then order_id end) as frequency_30d
    from {{ ref('stg_orders') }}
    cross join parameters p
    where created_at >= (p.snapshot_date - interval '60 days')
      and created_at < p.snapshot_date
      and status not in ('Returned', 'Cancelled')
    group by 1
),

engagement as (
    select
        user_id,
        count(*) as total_events_all_time,
        count(case when event_type = 'product' then 1 end) as view_count,
        count(case when event_type = 'cart' then 1 end) as cart_count,
        count(case when event_type = 'purchase' then 1 end) as purchase_event_count,
        count(distinct session_id) as unique_sessions
    from base_events
    group by 1
)

select
    u.user_id,
    p.snapshot_date,
    
    -- Demographics
    u.traffic_source,
    u.country,
    u.gender,
    
    -- RFM Features
    coalesce(rfm.frequency_all_time, 0) as frequency_all_time,
    coalesce(w_rfm.frequency_60d, 0) as frequency_60d,
    coalesce(w_rfm.frequency_30d, 0) as frequency_30d,
    (EXTRACT(EPOCH FROM (p.snapshot_date - rfm.last_order_date)) / 86400)::int as recency_days,
    (EXTRACT(EPOCH FROM (p.snapshot_date - rfm.first_order_date)) / 86400)::int as tenure_days,
    
    -- Engagement Features
    coalesce(eng.total_events_all_time, 0) as total_events,
    coalesce(eng.view_count, 0) as view_count,
    coalesce(eng.cart_count, 0) as cart_count,
    coalesce(eng.unique_sessions, 0) as session_count,
    
    -- Ratios
    case when coalesce(eng.view_count, 0) > 0 
         then coalesce(eng.cart_count, 0)::float / eng.view_count 
         else 0 
    end as view_to_cart_rate

from users u -- Universe is ALL users, though we typically train on active ones
left join rfm on u.user_id = rfm.user_id
left join windowed_rfm w_rfm on u.user_id = w_rfm.user_id
left join engagement eng on u.user_id = eng.user_id
cross join parameters p
where rfm.frequency_all_time > 0 -- Only customers who have purchased at least once ever
