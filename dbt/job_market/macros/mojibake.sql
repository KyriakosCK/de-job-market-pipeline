{#
    Mojibake: UTF-8 text wrongly decoded as Latin-1, e.g. "Macaé" stored as
    "MacaÃ©". Its signature is a UTF-8 lead byte (U+00C2-U+00F4) followed by
    a continuation byte (U+0080-U+00BF), a pair that almost never occurs in
    real text.

    Ingestion repairs this at the edge (ingestion/transform.py ::
    repair_mojibake). These macros are the backstop for anything that can't
    be repaired, such as a multi-byte character truncated by the source.
#}

{% macro is_mojibake(column_name) %}
    ({{ column_name }} ~ '[Â-ô][\u0080-¿]')
{% endmacro %}

{# Non-ASCII text with no Latin letters at all, e.g. "دبي" or "東京".
   "São Paulo" or "Zürich" don't match. #}
{% macro is_non_latin(column_name) %}
    ({{ column_name }} ~ '[^\x01-\x7f]' and {{ column_name }} !~ '[A-Za-z]')
{% endmacro %}

{% macro null_if_mojibake(column_name) %}
    case when {{ is_mojibake(column_name) }} then null else {{ column_name }} end
{% endmacro %}
