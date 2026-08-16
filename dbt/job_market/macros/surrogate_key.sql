{% macro surrogate_key(column_name) %}
    md5(lower(trim(cast({{ column_name }} as varchar))))
{% endmacro %}
