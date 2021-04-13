# hacs_hdo
Home assistant ČEZ HDO integration


## Template

```gotemplate
### HDO {% if is_state('binary_sensor.nizky_tarif','on') %}▼{% else %}▲{%endif%}

 {% for h in states.binary_sensor.nizky_tarif.attributes.following%}{{h.start.strftime('%H:%M')}}▼ {{h.end.strftime('%H:%M')}}▲ {% endfor %}

---
{% if is_state('sensor.cez_distribuce_planovane_odstavky', 'off') %}**žádné** plánované odstávky elektřiny
{% else %}
následující plánovaná odstávka elektřiny je od **{{states.sensor.cez_distribuce_planovane_odstavky.attributes.times[0].from}}** do
{{states.sensor.cez_distribuce_planovane_odstavky.attributes.times[0].to}}{%endif%}


```