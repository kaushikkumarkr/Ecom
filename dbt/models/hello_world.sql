
-- Models usually go in staging or marts, but for hello world we can put it at root of models or a demo folder.
-- We will put it in staging for now as a test.

/*
  A simple 'Hello World' model.
  It selects 1 as id and 'Hello World' as message.
*/

select
    1 as id,
    'Hello World' as message,
    current_timestamp as created_at
