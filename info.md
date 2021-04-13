# hacs_hdo
Home assistant ČEZ HDO integration


## Template

```gotemplate
### HDO {% if is_state('binary_sensor.nizky_tarif','on') %}▼{% else %}▲{%endif%}

 {% for h in states.binary_sensor.nizky_tarif.attributes.following%}{{h.start.strftime('%H:%M')}}▼ {{h.end.strftime('%H:%M')}}▲ {% endfor %}


```