with user_cohorts as (
    -- Define the Cohort: When did we first see the user?
    select
        user_id,
        date_trunc('week', min(session_start_at))::date as cohort_week
    from {{ ref('fct_sessions') }}
    group by 1
),

user_activities as (
    -- Define Activity: When was the user active?
    select
        s.user_id,
        date_trunc('week', s.session_start_at)::date as activity_week
    from {{ ref('fct_sessions') }} s
    group by 1, 2
),

cohort_activities as (
    -- Join Cohort + Activity to calculate "Age"
    select
        uc.user_id,
        uc.cohort_week,
        ua.activity_week,
        -- Calculate weeks since first seen. 
        -- Note: Postgres subtraction of dates gives days. /7 to get weeks.
        (ua.activity_week - uc.cohort_week) / 7 as period_number
    from user_cohorts uc
    join user_activities ua on uc.user_id = ua.user_id
),

cohort_size as (
    -- Denominator: How many users originally in the cohort?
    select
        cohort_week,
        count(distinct user_id) as cohort_users
    from user_cohorts
    group by 1
),

retention_counts as (
    -- Numerator: How many of them came back in period N?
    select
        cohort_week,
        period_number,
        count(distinct user_id) as active_users
    from cohort_activities
    group by 1, 2
)

select
    rc.cohort_week,
    rc.period_number,
    cs.cohort_users as initial_users,
    rc.active_users,
    -- Retention Rate
    rc.active_users * 1.0 / cs.cohort_users as retention_rate
from retention_counts rc
join cohort_size cs on rc.cohort_week = cs.cohort_week
order by 1, 2
