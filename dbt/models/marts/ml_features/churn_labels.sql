-- Logic:
-- 1. Snapshot Date: '2023-09-01' (Traffic Split/Cutoff).
-- 2. Prediction Horizon: 30 Days (2023-09-01 to 2023-10-01).
-- 3. Target: Did the user purchase? (0 = No Purchase = Churn, 1 = Purchase = Retained).
-- Note: Often Churn=1 means "Left". So if orders=0, is_churned=1.

with parameters as (
    select '2023-09-01'::timestamp as snapshot_date
),

active_users as (
    -- Users active in the 60 days strict PRIOR to snapshot
    select distinct user_id
    from {{ ref('stg_orders') }}
    cross join parameters p
    where created_at >= (p.snapshot_date - interval '60 days')
      and created_at < p.snapshot_date
      and status not in ('Returned', 'Cancelled')
),

future_activity as (
    -- Purchases in the 30 days AFTER snapshot
    select
        user_id,
        count(distinct order_id) as future_orders
    from {{ ref('stg_orders') }}
    cross join parameters p
    where created_at >= p.snapshot_date
      and created_at < (p.snapshot_date + interval '30 days')
      and status not in ('Returned', 'Cancelled')
    group by 1
)

select
    au.user_id,
    p.snapshot_date,
    case 
        when coalesce(fa.future_orders, 0) = 0 then 1 -- No Orders = Churned
        else 0 -- Orders = Retained
    end as is_churned
from active_users au
left join future_activity fa on au.user_id = fa.user_id
cross join parameters p
