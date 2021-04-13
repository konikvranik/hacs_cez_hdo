[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg?style=for-the-badge)](https://github.com/custom-components/hacs)
# hacs_cez

Home assistant ČEZ HDO integration


## Template

```gotemplate
### HDO {% if is_state('binary_sensor.nizky_tarif','on') %}▼{% else %}▲{%endif%}

 {% for h in states.binary_sensor.nizky_tarif.attributes.following%}{{h.start.strftime('%H:%M')}}▼ {{h.end.strftime('%H:%M')}}▲ {% endfor %}

```