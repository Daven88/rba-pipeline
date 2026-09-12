{% test not_empty(model) %}

select 1
from (select count(*) as n from {{ model }})
where n = 0

{% endtest %}