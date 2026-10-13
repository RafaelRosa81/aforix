# Decisiones metodologicas del calculo IVE

## Decision: uso de la desviacion estandar de velocidad

**Decision adoptada:** utilizar directamente `s_v,IVE`, estimada por el metodo IVE a partir de los residuos de velocidad observados entre verticales.

El motor utiliza:

`s_v,utilizado = s_v,IVE`

No se aplica un minimo instrumental adicional `s_v,min`.

## Alcance

- La decision se aplica al calculo IVE independientemente del instrumento.
- La resolucion instrumental del molinete no modifica la desviacion estandar de velocidad empleada por el motor.
- El modulo de resolucion instrumental, si se conserva, es una herramienta independiente y no participa en este calculo.
- Se mantienen los criterios existentes de aplicabilidad del metodo y los estados de calculo no disponible o no aplicable.

## Fundamento y limitaciones

Esta es una decision metodologica del proyecto Aforix. No demuestra que la resolucion instrumental carezca de importancia ni que el procedimiento sea equivalente a todos los criterios de la documentacion tecnica de referencia.

Para molinetes, la guia de referencia contempla un minimo instrumental de velocidad mediante el criterio `s_v = max(s_v,IVE, s_v,min)`. La decision adoptada en Aforix se aparta expresamente de ese criterio.

Para FlowTracker, debe distinguirse el calculo estadistico independiente de Aforix de la incertidumbre reportada por el software del instrumento. La equivalencia entre ambos resultados requiere validacion.

## Consecuencias para los resultados

- Los resultados se calculan con `s_v,IVE` sin aplicar `s_v,min`.
- Los informes deben dejar constancia de esta decision.
- El estado `calculated` indica que el motor realizo el calculo conforme al metodo implementado; no certifica por si solo el cumplimiento de una norma o guia externa.

## Revision futura

Revisar esta decision si se requiere cumplir estrictamente la guia aplicable, aparece nueva evidencia tecnica o una comparacion validada justifica cambiar el procedimiento.

Cualquier cambio futuro debe registrar las fuentes consultadas, el razonamiento, las pruebas de regresion y el impacto numerico sobre los aforos existentes.
