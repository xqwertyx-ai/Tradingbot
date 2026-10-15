# Experimento 2: deriva tras resultados empresariales (PEAD) — pre-registro

Escrito el 2026-10-15, **antes de descargar ni mirar ningún dato**. Cambiar estas reglas después de ver resultados invalida la prueba; si se cambian, se anota aquí con fecha y motivo.

## Hipótesis
Tras una sorpresa grande en resultados, el precio no la descuenta entera el día del anuncio y sigue moviéndose en la misma dirección durante días o semanas (Bernard y Thomas, 1989; Brandt y otros, 2008). Puede haberse debilitado desde que se publicó, sobre todo en grandes empresas.

## Datos
- Universo: componentes actuales del S&P 500 y del Nasdaq 100.
- Fechas de resultados, BPA estimado y real (yfinance) y precios diarios ajustados. Mercado de referencia: SPY.
- Sesgo conocido: solo empresas que existen hoy (supervivencia). Favorece a las compras; por eso todo se compara con una referencia del mismo universo y fechas.

## Sin información futura
- Día de reacción: si el anuncio es tras el cierre, la sesión siguiente; si es antes de la apertura o la hora es desconocida, se usa la ventana de dos sesiones (día del anuncio y siguiente).
- **Reacción anormal (RA)**: retorno de la acción menos el de SPY, del cierre previo al anuncio al cierre de la sesión de reacción (o de la sesión siguiente al anuncio si la hora es desconocida).
- **Entrada: cierre de la sesión siguiente a la de reacción** (un día de margen; conservador).
- Los umbrales de "sorpresa grande" se calculan solo con eventos de los 365 días anteriores a cada evento (percentiles 10 y 90). Nunca con eventos posteriores.

## Señales (fijadas)
1. **RA**: compra si la RA está en el 10% más alto de los últimos 365 días; venta si está en el 10% más bajo.
2. **BPA**: igual con la sorpresa de BPA en % (real frente a estimado), cuando exista.
3. **Ambas**: solo cuando RA y BPA están en el mismo extremo.

## Operación simulada
- Plazos: 5, 10, 20 y 40 sesiones desde la entrada.
- Dos versiones: acción sola, y acción cubierta con SPY (larga acción / corta SPY o al revés).
- Costes: 0,10% ida y vuelta en la acción; +0,02% en la cobertura con SPY.

## División exploración / prueba
- Exploración: eventos hasta el 30-sep-2025.
- **Prueba: eventos desde el 1-oct-2025** (que puedan cerrarse con los precios disponibles). La prueba se mira una sola vez.

## Criterio de éxito (sobre la prueba)
Una combinación (señal × lado × plazo × versión) pasa si cumple **todo**:
1. Retorno neto medio por operación **≥ 1%**.
2. Límite inferior del IC 95% del retorno neto medio > 0.
3. Supera a la referencia: misma media que todos los eventos del universo con el mismo plazo y versión (comprar en cada anuncio sin filtrar).
4. n ≥ 50 operaciones en prueba.
5. Ya funcionaba en exploración (misma dirección y retorno neto > 0).

Se prueban 3 señales × 2 lados × 4 plazos × 2 versiones = 48 combinaciones: alguna puede pasar por azar. Un aprobado aislado y por poco es una pista, no una prueba; la confirmación será el test en vivo.

## Fase 2 (solo si hay ventaja)
El agente de IA lee el titular de cada anuncio (por ejemplo, "bate pero rebaja previsiones") para filtrar. Se probará como una regla más, con la misma división exploración/prueba.
