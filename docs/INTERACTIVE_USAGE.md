# Modos interactivos de Aforix

Aforix tiene cuatro flujos interactivos operativos. Cada uno guía la selección de parámetros para una función concreta; no existe todavía un menú general que ejecute todas las funciones del programa.

## Exportación de tablas

Permite elegir la tabla normalizada, el instrumento, los puntos, el rango de fechas y el formato de salida.

```bash
aforix export tables -c configs/examples/main.yaml --interactive
```

Lee los datos de `database/normalized/` y guarda los archivos de exportación según la configuración.

## Exportación SIH

Guía la selección de mediciones que se exportarán al formato SIH.

```bash
aforix export sih -c configs/examples/main.yaml --sih-config configs/sih/sih.yaml --interactive
```

La exportación también puede ejecutarse con un archivo de selección CSV. Consulta `docs/SIH_EXPORT.md` y `docs/SIH_CONFIGURATION.md`.

## Análisis caudal–altura

Solicita instrumentos, puntos, fechas, fuentes de altura y opciones de salida.

```bash
aforix analyze stage-discharge interactive -c configs/examples/main.yaml
```

La guía del análisis está en `docs/STAGE_DISCHARGE_ANALYSIS.md`.

## Perfiles de sección

Guía la selección de instrumentos, puntos, fechas, ejes y tipo de gráfico.

```bash
aforix analyze section-profiles run -c configs/examples/main.yaml --interactive
```

Los tipos disponibles para esta funcionalidad son `scatter` y `bar`. Consulta `docs/SECTION_PROFILES_ANALYSIS.md`.

## Modo batch

Los comandos interactivos no se ejecutan dentro de un batch. Para automatizar, configura los parámetros directamente en el YAML batch. Consulta `docs/BATCH_GUIDE.md`.

## Launchers

Los launchers de Windows y Linux abren el entorno y ejecutan comandos batch. Su uso se describe en `docs/LAUNCHERS_GUIDE.md`.
