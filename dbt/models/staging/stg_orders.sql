with source as (

    select * from {{ source('thelook_ecommerce', 'orders') }}

),

renamed as (

    select
        order_id,
        user_id,
        status,
        gender,
        created_at::timestamp as created_at,
        returned_at::timestamp as returned_at,
        shipped_at::timestamp as shipped_at,
        delivered_at::timestamp as delivered_at,
        num_of_item

    from source

)

select * from renamed
