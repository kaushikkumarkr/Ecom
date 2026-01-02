with source as (

    select * from {{ source('thelook_ecommerce', 'users') }}

),

renamed as (

    select
        id as user_id,
        first_name,
        last_name,
        email,
        age,
        gender,
        state,
        street_address,
        postal_code,
        city,
        country,
        latitude,
        longitude,
        traffic_source,
        created_at,
        
        -- Derived
        concat(first_name, ' ', last_name) as full_name

    from source

)

select * from renamed
