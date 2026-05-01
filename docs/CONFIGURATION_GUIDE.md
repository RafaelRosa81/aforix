# Guía de configuración de Aforix

[...snip identical content...]

### 6.2 Molinete

Los archivos Molinete deben colocarse en:

```text
data/raw/ML/
```

Si el archivo es Excel, la hoja esperada por defecto es `CALCULO`, por ejemplo:

```yaml
molinete:
  raw_subdir: ML
  sheet_name: CALCULO
```

En Molinete, cargar el ID del punto en `ESTACION Nº:` y el nombre del punto en `NOMBRE:`.

[...rest unchanged...]