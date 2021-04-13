[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg?style=for-the-badge)](https://github.com/custom-components/hacs)
# hacs_cez

Home assistant ČEZ HDO integration


## Template

```gotemplate
### HDO {% if is_state('binary_sensor.nizky_proud','on') %}▼{% else %}▲{%endif%}

 {% for h in states.binary_sensor.nizky_proud.attributes.following%}{{h.start.strftime('%H:%M')}}▼ {{h.end.strftime('%H:%M')}}▲ {% endfor %}

---

{% if is_state('binary_sensor.planovane_vypadky_elektriny', 'on') %}
následující plánovaná odstávka elektřiny je od **{{states.binary_sensor.planovane_vypadky_elektriny.attributes.times[0].from}}** do
{{states.binary_sensor.planovane_vypadky_elektriny.attributes.times[0].to}}
{% else %}
**žádné** plánované odstávky elektřiny{%endif%}

```