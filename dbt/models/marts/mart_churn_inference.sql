-- Logic:
-- 1. Cutoff Date = MAX(created_at) (The "Present" in our dataset).
-- 2. Features: Computed using all available data.
-- 3. Target: NULL (Future is unknown).

with parameters as (
    select max(created_at)::date as cutoff_date
    from {{ ref('stg_orders') }}
),

-- 1. Universe: All users
valid_users as (
    select distinct user_id
    from {{ ref('stg_orders') }}
),

-- 2. Features: Behavior ALL TIME
past_performance as (
    select
        o.user_id,
        min(o.created_at)::date as first_order_date,
        max(o.created_at)::date as last_order_date,
        count(distinct o.order_id) as frequency,
        sum(1) as total_orders
    from {{ ref('stg_orders') }} o
    where o.status not in ('Returned', 'Cancelled')
    group by 1
),

monetary_agg as (
    select
        oi.user_id,
        sum(oi.sale_price) as total_spend
    from {{ ref('stg_order_items') }} oi
    join {{ ref('stg_orders') }} o on oi.order_id = o.order_id
    where o.status not in ('Returned', 'Cancelled')
    group by 1
)

select
    u.user_id,
    p.cutoff_date as snapshot_date,
    
    -- Independent Variables (Features)
    (p.cutoff_date - pp.last_order_date) as recency_days,
    pp.frequency,
    coalesce(m.total_spend, 0) as monetary,
    coalesce(m.total_spend, 0) / nullif(pp.frequency, 0) as avg_order_value,
    (p.cutoff_date - pp.first_order_date) as tenure_days

from valid_users u
join past_performance pp on u.user_id = pp.user_id
left join monetary_agg m on u.user_id = m.user_id
cross join parameters p
where pp.frequency > 0
