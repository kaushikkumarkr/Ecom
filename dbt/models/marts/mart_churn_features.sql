-- Logic:
-- 1. Setup a "Cutoff Date" (e.g. 2023-10-01).
-- 2. Features: Computed using only data BEFORE Cutoff Date.
-- 3. Target: Computed using data AFTER Cutoff Date.

with parameters as (
    select '2023-10-01'::timestamp as cutoff_date
),

-- 1. Universe: Users who joined BEFORE the cutoff
valid_users as (
    select distinct user_id
    from {{ ref('stg_orders') }}
    cross join parameters p
    where created_at < p.cutoff_date
),

-- 2. Features: Behavior BEFORE cutoff
past_performance as (
    select
        o.user_id,
        min(o.created_at)::date as first_order_date,
        max(o.created_at)::date as last_order_date,
        count(distinct o.order_id) as frequency,
        -- Need to join items for monetary.
        -- Approximating monetary via simple order count for speed/stability if items table is heavy,
        -- but let's try to join efficiently.
        sum(1) as total_orders -- Placeholder for monetary strength
    from {{ ref('stg_orders') }} o
    cross join parameters p
    where o.created_at < p.cutoff_date
    and o.status not in ('Returned', 'Cancelled')
    group by 1
),

monetary_agg as (
    select
        oi.user_id,
        sum(oi.sale_price) as total_spend
    from {{ ref('stg_order_items') }} oi
    join {{ ref('stg_orders') }} o on oi.order_id = o.order_id
    cross join parameters p
    where o.created_at < p.cutoff_date
    and o.status not in ('Returned', 'Cancelled')
    group by 1
),

-- 3. Target: Behavior AFTER cutoff (The "Future")
future_behavior as (
    select
        user_id,
        count(distinct order_id) as future_orders
    from {{ ref('stg_orders') }}
    cross join parameters p
    where created_at >= p.cutoff_date
    and status not in ('Returned', 'Cancelled')
    group by 1
)

select
    u.user_id,
    p.cutoff_date as snapshot_date,
    
    -- Independent Variables (Features)
    -- Recency: Days between Last active date and Cutoff Date
    (p.cutoff_date::date - pp.last_order_date) as recency_days,
    
    pp.frequency,
    coalesce(m.total_spend, 0) as monetary,
    coalesce(m.total_spend, 0) / nullif(pp.frequency, 0) as avg_order_value,
    (p.cutoff_date::date - pp.first_order_date) as tenure_days,
    
    -- Dependent Variable (Target)
    -- If they have 0 future orders, they Churned.
    -- If they have > 0 future orders, they Retained.
    case 
        when coalesce(fb.future_orders, 0) = 0 then 1 -- CHURNED
        else 0 -- RETAINED
    end as is_churned

from valid_users u
join past_performance pp on u.user_id = pp.user_id
left join monetary_agg m on u.user_id = m.user_id
left join future_behavior fb on u.user_id = fb.user_id
cross join parameters p
where pp.frequency > 0 -- Only scoring customers who actually bought something
