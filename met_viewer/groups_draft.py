"""Borrador de grupos generado por grouping.py. Revisar y guardar como groups.py.

GROUPS: por variable. Clave = variable; valor = lista de grupos (una figura por grupo).
    Una estación puede estar en más de un grupo de la misma variable.
GROUPS_COMBINED: un solo agrupamiento para todas las variables (distancia combinada de
    T y HR). Lo usa la vista por grupo."""

# Periodo: 2025-11-13 → 2026-11-13
# == AirTC_Avg
# G1 (7), r medio 0.87: Altarani, Apacheta, Camp_Quellaveco, Charaque, Mina_Norte, Papujune, Planta_Concentradora
# G2 (6), r medio 0.89: Alto_Tala, Calientes1, Chalsos, Cortadera, Dique_pie_botadero, Tala_Legal
# G3 (4), r medio 0.86: Alto_Quellaveco, Mina_Norte, Minas_Sur, Sarallenque_MQG-15-02
# G4 (3), r medio 0.84: Alto_Tala, Cerro_Salviani, Cortadera
# G5 (3), r medio 0.84: Chancado_primario, Dique_pie_botadero, Tala_Legal
# G6 (3), r medio 0.79: Dique_pie_botadero, Minas_Sur, Tala-1
# G7 (3), r medio 0.90: Huachunta, Titire, Vizcachas
# G8 (2), r medio 0.74: Calacaja, DME3_Cortadera
#
# Vizcachas              mediana    2.5 -> Huachunta r=0.91 (6 km); Titire r=0.87 (11 km); Altarani r=0.45 (58 km)
# Huachunta              mediana    2.9 -> Vizcachas r=0.91 (6 km); Titire r=0.90 (16 km); Altarani r=0.44 (52 km)
# Titire                 mediana    3.7 -> Huachunta r=0.90 (16 km); Vizcachas r=0.87 (11 km); Chancado_primario r=0.45 (65 km)
# Sarallenque_MQG-15-02  mediana    5.3 -> Alto_Quellaveco r=0.91 (5 km); Minas_Sur r=0.89 (4 km); Planta_Concentradora r=0.86 (7 km)
# Minas_Sur              mediana    6.5 -> Alto_Quellaveco r=0.90 (1 km); Planta_Concentradora r=0.90 (5 km); Sarallenque_MQG-15-02 r=0.89 (4 km)
# Papujune               mediana    6.9 -> Planta_Concentradora r=0.92 (2 km); Charaque r=0.90 (4 km); Apacheta r=0.89 (7 km)
# Altarani               mediana    7.4 -> Charaque r=0.91 (6 km); Minas_Sur r=0.87 (1 km); Planta_Concentradora r=0.87 (7 km)
# Planta_Concentradora   mediana    7.7 -> Papujune r=0.92 (2 km); Apacheta r=0.91 (6 km); Minas_Sur r=0.90 (5 km)
# Mina_Norte             mediana    8.0 -> Planta_Concentradora r=0.88 (5 km); Papujune r=0.88 (5 km); Minas_Sur r=0.86 (4 km)
# Alto_Quellaveco        mediana    8.0 -> Sarallenque_MQG-15-02 r=0.91 (5 km); Minas_Sur r=0.90 (1 km); Planta_Concentradora r=0.89 (5 km)
# Charaque               mediana    8.3 -> Altarani r=0.91 (6 km); Camp_Quellaveco r=0.90 (3 km); Dique_pie_botadero r=0.90 (2 km)
# Apacheta               mediana    8.7 -> Planta_Concentradora r=0.91 (6 km); Papujune r=0.89 (7 km); Alto_Tala r=0.88 (9 km)
# Camp_Quellaveco        mediana    8.9 -> Charaque r=0.90 (3 km); Dique_pie_botadero r=0.87 (3 km); Altarani r=0.87 (4 km)
# Tala-1                 mediana    9.1 -> Dique_pie_botadero r=0.82 (1 km); Mina_Norte r=0.81 (4 km); Minas_Sur r=0.81 (7 km)
# Alto_Tala              mediana    9.3 -> Dique_pie_botadero r=0.93 (1 km); Tala_Legal r=0.90 (1 km); Cortadera r=0.89 (9 km)
# Cerro_Salviani         mediana    9.7 -> Alto_Tala r=0.82 (4 km); Cortadera r=0.80 (6 km); Mina_Norte r=0.79 (8 km)
# Tala_Legal             mediana    9.9 -> Dique_pie_botadero r=0.94 (2 km); Cortadera r=0.91 (9 km); Alto_Tala r=0.90 (1 km)
# Chancado_primario      mediana   10.1 -> Dique_pie_botadero r=0.79 (3 km); Tala_Legal r=0.79 (5 km); Charaque r=0.78 (2 km)
# Cortadera              mediana   10.3 -> Tala_Legal r=0.91 (9 km); Chalsos r=0.91 (4 km); Dique_pie_botadero r=0.90 (9 km)
# Chalsos                mediana   10.5 -> Cortadera r=0.91 (4 km); Calientes1 r=0.89 (10 km); Tala_Legal r=0.89 (13 km)
# Dique_pie_botadero     mediana   10.9 -> Tala_Legal r=0.94 (2 km); Alto_Tala r=0.93 (1 km); Charaque r=0.90 (2 km)
# Calientes1             mediana   11.8 -> Chalsos r=0.89 (10 km); Tala_Legal r=0.89 (6 km); Cortadera r=0.88 (6 km)
# DME3_Cortadera         mediana   13.3 -> Calientes1 r=0.87 (7 km); Chalsos r=0.81 (8 km); Cortadera r=0.76 (7 km)
# Calacaja               mediana   16.2 -> DME3_Cortadera r=0.74 (8 km); Calientes1 r=0.68 (13 km); Chalsos r=0.62 (16 km)
# Mina_Norte: registro corto, asignada después (G1 r=0.85, G3 r=0.82; margen 0.033; en los dos grupos)
#
# == RH_Avg
# G1 (6), r medio 0.94: Alto_Tala, Camp_Quellaveco, Charaque, Dique_pie_botadero, Tala-1, Tala_Legal
# G2 (5), r medio 0.73: Calacaja, Calientes1, Chalsos, Cortadera, DME3_Cortadera
# G3 (5), r medio 0.93: Altarani, Alto_Quellaveco, Mina_Norte, Minas_Sur, Sarallenque_MQG-15-02
# G4 (4), r medio 0.90: Apacheta, Cerro_Salviani, Papujune, Planta_Concentradora
# G5 (4), r medio 0.90: Camp_Quellaveco, Chancado_primario, Dique_pie_botadero, Mina_Norte
# G6 (3), r medio 0.89: Huachunta, Titire, Vizcachas
#
# Mina_Norte             mediana   30.2 -> Charaque r=0.95 (2 km); Altarani r=0.93 (5 km); Planta_Concentradora r=0.93 (5 km)
# Alto_Tala              mediana   36.0 -> Tala-1 r=0.96 (1 km); Tala_Legal r=0.96 (1 km); Dique_pie_botadero r=0.95 (1 km)
# Minas_Sur              mediana   36.0 -> Alto_Quellaveco r=0.98 (1 km); Altarani r=0.97 (1 km); Sarallenque_MQG-15-02 r=0.96 (4 km)
# Alto_Quellaveco        mediana   36.4 -> Minas_Sur r=0.98 (1 km); Altarani r=0.92 (2 km); Sarallenque_MQG-15-02 r=0.92 (5 km)
# Camp_Quellaveco        mediana   37.1 -> Charaque r=0.95 (3 km); Tala-1 r=0.95 (4 km); Dique_pie_botadero r=0.93 (3 km)
# Apacheta               mediana   37.6 -> Papujune r=0.89 (7 km); Planta_Concentradora r=0.88 (6 km); Cerro_Salviani r=0.88 (6 km)
# Dique_pie_botadero     mediana   38.4 -> Tala_Legal r=0.97 (2 km); Tala-1 r=0.97 (1 km); Alto_Tala r=0.95 (1 km)
# Cortadera              mediana   38.5 -> Chalsos r=0.89 (4 km); Cerro_Salviani r=0.89 (6 km); Apacheta r=0.86 (4 km)
# Tala-1                 mediana   38.5 -> Dique_pie_botadero r=0.97 (1 km); Charaque r=0.96 (2 km); Alto_Tala r=0.96 (1 km)
# Altarani               mediana   38.6 -> Minas_Sur r=0.97 (1 km); Mina_Norte r=0.93 (5 km); Charaque r=0.92 (6 km)
# Planta_Concentradora   mediana   38.7 -> Papujune r=0.96 (2 km); Minas_Sur r=0.93 (5 km); Mina_Norte r=0.93 (5 km)
# Tala_Legal             mediana   39.1 -> Dique_pie_botadero r=0.97 (2 km); Tala-1 r=0.96 (2 km); Alto_Tala r=0.96 (1 km)
# Charaque               mediana   39.2 -> Tala-1 r=0.96 (2 km); Mina_Norte r=0.95 (2 km); Camp_Quellaveco r=0.95 (3 km)
# Cerro_Salviani         mediana   40.8 -> Papujune r=0.92 (2 km); Alto_Tala r=0.89 (4 km); Tala-1 r=0.89 (4 km)
# Papujune               mediana   40.8 -> Planta_Concentradora r=0.96 (2 km); Charaque r=0.92 (4 km); Tala-1 r=0.92 (2 km)
# Chancado_primario      mediana   41.6 -> Dique_pie_botadero r=0.92 (3 km); Camp_Quellaveco r=0.92 (1 km); Tala-1 r=0.92 (3 km)
# Calacaja               mediana   41.8 -> DME3_Cortadera r=0.73 (8 km); Calientes1 r=0.60 (13 km); Chalsos r=0.53 (16 km)
# Calientes1             mediana   42.1 -> Tala_Legal r=0.87 (6 km); Dique_pie_botadero r=0.85 (7 km); Cortadera r=0.84 (6 km)
# DME3_Cortadera         mediana   43.5 -> Calientes1 r=0.82 (7 km); Chalsos r=0.80 (8 km); Calacaja r=0.73 (8 km)
# Sarallenque_MQG-15-02  mediana   44.4 -> Minas_Sur r=0.96 (4 km); Alto_Quellaveco r=0.92 (5 km); Altarani r=0.91 (4 km)
# Chalsos                mediana   46.4 -> Cortadera r=0.89 (4 km); Calientes1 r=0.83 (10 km); Cerro_Salviani r=0.81 (10 km)
# Huachunta              mediana   63.2 -> Vizcachas r=0.92 (6 km); Titire r=0.86 (16 km); Minas_Sur r=0.53 (53 km)
# Vizcachas              mediana   63.8 -> Huachunta r=0.92 (6 km); Titire r=0.88 (11 km); Minas_Sur r=0.49 (59 km)
# Titire                 mediana   64.3 -> Vizcachas r=0.88 (11 km); Huachunta r=0.86 (16 km); Minas_Sur r=0.55 (65 km)
# Mina_Norte: registro corto, asignada después (G3 r=0.91, G5 r=0.88; margen 0.037; en los dos grupos)
#
# == WS_ms_Avg
# G1 (5), cos medio 0.92: Altarani, Alto_Quellaveco, Calientes1, Minas_Sur, Tala_Legal
# G2 (4), cos medio 0.84: Apacheta, Cerro_Salviani, Chancado_primario, DME3_Cortadera
# G3 (4), cos medio 0.97: Charaque, Cortadera, Papujune, Sarallenque_MQG-15-02
# G4 (3), cos medio 0.78: Alto_Quellaveco, Planta_Concentradora, Tala_Legal
# G5 (3), cos medio 0.97: Alto_Tala, Mina_Norte, Tala-1
# G6 (3), cos medio 0.90: Huachunta, Titire, Vizcachas
#
# Cerro_Salviani         mediana    1.3 -> Apacheta cos=0.93 (6 km); Chancado_primario cos=0.89 (6 km); Papujune cos=0.88 (2 km)
# Chancado_primario      mediana    1.4 -> Apacheta cos=0.97 (8 km); Cerro_Salviani cos=0.89 (6 km); Papujune cos=0.89 (4 km)
# Camp_Quellaveco        mediana    1.4 -> Alto_Quellaveco cos=0.92 (3 km); Mina_Norte cos=0.89 (2 km); Calientes1 cos=0.86 (10 km)
# Mina_Norte             mediana    1.7 -> Tala-1 cos=0.97 (4 km); Alto_Tala cos=0.96 (5 km); Cortadera cos=0.94 (12 km)
# Vizcachas              mediana    1.7 -> Huachunta cos=0.94 (6 km); Titire cos=0.82 (11 km); Chancado_primario cos=0.75 (59 km)
# Calacaja               mediana    1.8 -> DME3_Cortadera cos=0.70 (8 km); Chancado_primario cos=0.67 (23 km); Sarallenque_MQG-15-02 cos=0.58 (27 km)
# Huachunta              mediana    1.8 -> Vizcachas cos=0.94 (6 km); Titire cos=0.93 (16 km); Cerro_Salviani cos=0.74 (59 km)
# Papujune               mediana    1.9 -> Sarallenque_MQG-15-02 cos=1.00 (8 km); Cortadera cos=0.98 (7 km); Charaque cos=0.95 (4 km)
# Titire                 mediana    1.9 -> Huachunta cos=0.93 (16 km); Vizcachas cos=0.82 (11 km); Camp_Quellaveco cos=0.64 (65 km)
# Alto_Tala              mediana    2.0 -> Tala-1 cos=0.99 (1 km); Charaque cos=0.97 (3 km); Cortadera cos=0.96 (9 km)
# DME3_Cortadera         mediana    2.0 -> Chancado_primario cos=0.87 (16 km); Apacheta cos=0.79 (11 km); Calacaja cos=0.70 (8 km)
# Apacheta               mediana    2.3 -> Chancado_primario cos=0.97 (8 km); Cerro_Salviani cos=0.93 (6 km); Papujune cos=0.92 (7 km)
# Planta_Concentradora   mediana    2.4 -> Tala_Legal cos=0.75 (4 km); Alto_Quellaveco cos=0.64 (5 km); Calientes1 cos=0.63 (7 km)
# Minas_Sur              mediana    2.4 -> Calientes1 cos=0.97 (12 km); Alto_Quellaveco cos=0.96 (1 km); Charaque cos=0.96 (6 km)
# Charaque               mediana    2.6 -> Cortadera cos=0.98 (11 km); Alto_Tala cos=0.97 (3 km); Minas_Sur cos=0.96 (6 km)
# Alto_Quellaveco        mediana    2.6 -> Minas_Sur cos=0.96 (1 km); Calientes1 cos=0.96 (11 km); Tala_Legal cos=0.95 (8 km)
# Tala_Legal             mediana    2.8 -> Calientes1 cos=0.96 (6 km); Alto_Quellaveco cos=0.95 (8 km); Minas_Sur cos=0.95 (8 km)
# Cortadera              mediana    2.9 -> Charaque cos=0.98 (11 km); Papujune cos=0.98 (7 km); Sarallenque_MQG-15-02 cos=0.97 (14 km)
# Sarallenque_MQG-15-02  mediana    3.0 -> Papujune cos=1.00 (8 km); Cortadera cos=0.97 (14 km); Charaque cos=0.94 (4 km)
# Altarani               mediana    3.2 -> Tala_Legal cos=0.92 (9 km); Calientes1 cos=0.87 (14 km); Alto_Quellaveco cos=0.85 (2 km)
# Calientes1             mediana    3.4 -> Minas_Sur cos=0.97 (12 km); Tala_Legal cos=0.96 (6 km); Alto_Quellaveco cos=0.96 (11 km)
# Tala-1                 mediana    3.5 -> Alto_Tala cos=0.99 (1 km); Mina_Norte cos=0.97 (4 km); Charaque cos=0.95 (2 km)
# Dique_pie_botadero     mediana    3.5 -> Camp_Quellaveco cos=0.68 (3 km); Cerro_Salviani cos=0.63 (4 km); Titire cos=0.58 (66 km)
# G1: diferencia de ciclo de velocidad con el resto del grupo, máx 0.15
# G2: diferencia de ciclo de velocidad con el resto del grupo, máx 0.17
# G3: diferencia de ciclo de velocidad con el resto del grupo, máx 0.08
# G4: diferencia de ciclo de velocidad con el resto del grupo, máx 0.14
# G5: diferencia de ciclo de velocidad con el resto del grupo, máx 0.14
# G6: diferencia de ciclo de velocidad con el resto del grupo, máx 0.13
# Sin pareja (parecido medio < 0.6), una figura cada una: Calacaja
# Ciclo de velocidad distinto (diferencia media > 0.25), una figura cada una: Camp_Quellaveco, Dique_pie_botadero
# Fuera del agrupamiento (stations.WIND_EXCLUDED), una figura cada una: Chalsos, Sarallenque
#
# == combinado (T, HR)
# Mina_Norte: registro corto, asignada después (G5 r=0.87, G3 r=0.86; margen 0.004; en los dos grupos)
# G1 (6), r medio 0.89: Altarani, Alto_Tala, Camp_Quellaveco, Charaque, Dique_pie_botadero, Tala_Legal
# G2 (5), r medio 0.75: Calacaja, Calientes1, Chalsos, Cortadera, DME3_Cortadera
# G3 (4), r medio 0.89: Alto_Quellaveco, Mina_Norte, Minas_Sur, Sarallenque_MQG-15-02
# G4 (3), r medio 0.86: Alto_Tala, Cerro_Salviani, Papujune
# G5 (4), r medio 0.89: Apacheta, Mina_Norte, Papujune, Planta_Concentradora
# G6 (3), r medio 0.87: Camp_Quellaveco, Chancado_primario, Dique_pie_botadero
# G7 (3), r medio 0.85: Dique_pie_botadero, Minas_Sur, Tala-1
# G8 (3), r medio 0.89: Huachunta, Titire, Vizcachas

GROUPS: dict[str, list[list[str]]] = {
    'AirTC_Avg': [
        ['Altarani', 'Apacheta', 'Camp_Quellaveco', 'Charaque', 'Mina_Norte', 'Papujune', 'Planta_Concentradora'],
        ['Alto_Tala', 'Calientes1', 'Chalsos', 'Cortadera', 'Dique_pie_botadero', 'Tala_Legal'],
        ['Alto_Quellaveco', 'Mina_Norte', 'Minas_Sur', 'Sarallenque_MQG-15-02'],
        ['Alto_Tala', 'Cerro_Salviani', 'Cortadera'],
        ['Chancado_primario', 'Dique_pie_botadero', 'Tala_Legal'],
        ['Dique_pie_botadero', 'Minas_Sur', 'Tala-1'],
        ['Huachunta', 'Titire', 'Vizcachas'],
        ['Calacaja', 'DME3_Cortadera'],
        ['Ilo'],
    ],
    'RH_Avg': [
        ['Alto_Tala', 'Camp_Quellaveco', 'Charaque', 'Dique_pie_botadero', 'Tala-1', 'Tala_Legal'],
        ['Calacaja', 'Calientes1', 'Chalsos', 'Cortadera', 'DME3_Cortadera'],
        ['Altarani', 'Alto_Quellaveco', 'Mina_Norte', 'Minas_Sur', 'Sarallenque_MQG-15-02'],
        ['Apacheta', 'Cerro_Salviani', 'Papujune', 'Planta_Concentradora'],
        ['Camp_Quellaveco', 'Chancado_primario', 'Dique_pie_botadero', 'Mina_Norte'],
        ['Huachunta', 'Titire', 'Vizcachas'],
        ['Ilo'],
    ],
    'WS_ms_Avg': [
        ['Altarani', 'Alto_Quellaveco', 'Calientes1', 'Minas_Sur', 'Tala_Legal'],
        ['Apacheta', 'Cerro_Salviani', 'Chancado_primario', 'DME3_Cortadera'],
        ['Charaque', 'Cortadera', 'Papujune', 'Sarallenque_MQG-15-02'],
        ['Alto_Quellaveco', 'Planta_Concentradora', 'Tala_Legal'],
        ['Alto_Tala', 'Mina_Norte', 'Tala-1'],
        ['Huachunta', 'Titire', 'Vizcachas'],
        ['Calacaja'],
        ['Camp_Quellaveco'],
        ['Dique_pie_botadero'],
        ['Chalsos'],
        ['Sarallenque'],
        ['Ilo'],
    ],
}

GROUPS_COMBINED: list[list[str]] = [
    ['Altarani', 'Alto_Tala', 'Camp_Quellaveco', 'Charaque', 'Dique_pie_botadero', 'Tala_Legal'],
    ['Calacaja', 'Calientes1', 'Chalsos', 'Cortadera', 'DME3_Cortadera'],
    ['Alto_Quellaveco', 'Mina_Norte', 'Minas_Sur', 'Sarallenque_MQG-15-02'],
    ['Alto_Tala', 'Cerro_Salviani', 'Papujune'],
    ['Apacheta', 'Mina_Norte', 'Papujune', 'Planta_Concentradora'],
    ['Camp_Quellaveco', 'Chancado_primario', 'Dique_pie_botadero'],
    ['Dique_pie_botadero', 'Minas_Sur', 'Tala-1'],
    ['Huachunta', 'Titire', 'Vizcachas'],
    ['Ilo'],
]
