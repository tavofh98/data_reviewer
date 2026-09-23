"""Borrador de grupos generado por grouping.py. Revisar y guardar como groups.py.

GROUPS: por variable. Clave = variable; valor = lista de grupos (una figura por grupo).
    Una estación puede estar en más de un grupo de la misma variable.
GROUPS_COMBINED: un solo agrupamiento para todas las variables (distancia combinada de
    T y HR). Lo usa la vista por grupo."""

# Periodo: 2025-09-19 → 2026-09-19
# == AirTC_Avg
# G1 (6), r medio 0.87: Altarani, Apacheta, Camp_Quellaveco, Charaque, Papujune, Planta_Concentradora
# G2 (6), r medio 0.89: Alto_Tala, Calientes1, Chalsos, Cortadera, Dique_pie_botadero, Tala_Legal
# G3 (4), r medio 0.80: Alto_Quellaveco, Cerro_Salviani, Minas_Sur, Sarallenque_MQG-15-02
# G4 (4), r medio 0.77: Calacaja, Calientes1, Chalsos, DME3_Cortadera
# G5 (3), r medio 0.84: Chancado_primario, Dique_pie_botadero, Tala_Legal
# G6 (3), r medio 0.79: Dique_pie_botadero, Minas_Sur, Tala-1
# G7 (3), r medio 0.92: Huachunta, Titire, Vizcachas
#
# Vizcachas              mediana    2.5 -> Huachunta r=0.94 (6 km); Titire r=0.90 (11 km); Altarani r=0.47 (58 km)
# Huachunta              mediana    2.9 -> Vizcachas r=0.94 (6 km); Titire r=0.90 (16 km); Altarani r=0.44 (52 km)
# Titire                 mediana    3.7 -> Huachunta r=0.90 (16 km); Vizcachas r=0.90 (11 km); Chancado_primario r=0.45 (65 km)
# Sarallenque_MQG-15-02  mediana    5.2 -> Alto_Quellaveco r=0.91 (5 km); Minas_Sur r=0.88 (4 km); Planta_Concentradora r=0.86 (7 km)
# Minas_Sur              mediana    6.1 -> Planta_Concentradora r=0.89 (5 km); Sarallenque_MQG-15-02 r=0.88 (4 km); Alto_Quellaveco r=0.88 (1 km)
# Papujune               mediana    6.8 -> Planta_Concentradora r=0.92 (2 km); Charaque r=0.90 (4 km); Apacheta r=0.89 (7 km)
# Altarani               mediana    7.3 -> Charaque r=0.91 (6 km); Planta_Concentradora r=0.87 (7 km); Camp_Quellaveco r=0.87 (4 km)
# Planta_Concentradora   mediana    7.7 -> Papujune r=0.92 (2 km); Apacheta r=0.91 (6 km); Minas_Sur r=0.89 (5 km)
# Alto_Quellaveco        mediana    7.9 -> Sarallenque_MQG-15-02 r=0.91 (5 km); Planta_Concentradora r=0.88 (5 km); Minas_Sur r=0.88 (1 km)
# Charaque               mediana    8.2 -> Altarani r=0.91 (6 km); Camp_Quellaveco r=0.90 (3 km); Papujune r=0.90 (4 km)
# Apacheta               mediana    8.6 -> Planta_Concentradora r=0.91 (6 km); Papujune r=0.89 (7 km); Alto_Tala r=0.87 (9 km)
# Camp_Quellaveco        mediana    8.7 -> Charaque r=0.90 (3 km); Dique_pie_botadero r=0.87 (3 km); Altarani r=0.87 (4 km)
# Tala-1                 mediana    9.1 -> Dique_pie_botadero r=0.82 (1 km); Minas_Sur r=0.81 (7 km); Charaque r=0.71 (2 km)
# Alto_Tala              mediana    9.2 -> Dique_pie_botadero r=0.93 (1 km); Tala_Legal r=0.90 (1 km); Cortadera r=0.89 (9 km)
# Cerro_Salviani         mediana    9.6 -> Minas_Sur r=0.78 (8 km); Alto_Tala r=0.78 (4 km); Cortadera r=0.77 (6 km)
# Tala_Legal             mediana    9.8 -> Dique_pie_botadero r=0.95 (2 km); Cortadera r=0.91 (9 km); Alto_Tala r=0.90 (1 km)
# Chancado_primario      mediana    9.9 -> Dique_pie_botadero r=0.79 (3 km); Tala_Legal r=0.79 (5 km); Charaque r=0.77 (2 km)
# Cortadera              mediana   10.2 -> Tala_Legal r=0.91 (9 km); Chalsos r=0.91 (4 km); Dique_pie_botadero r=0.90 (9 km)
# Chalsos                mediana   10.4 -> Cortadera r=0.91 (4 km); Calientes1 r=0.89 (10 km); Tala_Legal r=0.89 (13 km)
# Dique_pie_botadero     mediana   10.8 -> Tala_Legal r=0.95 (2 km); Alto_Tala r=0.93 (1 km); Cortadera r=0.90 (9 km)
# Calientes1             mediana   11.7 -> Chalsos r=0.89 (10 km); Tala_Legal r=0.89 (6 km); Cortadera r=0.88 (6 km)
# DME3_Cortadera         mediana   13.1 -> Calientes1 r=0.87 (7 km); Chalsos r=0.81 (8 km); Cortadera r=0.76 (7 km)
# Calacaja               mediana   16.0 -> DME3_Cortadera r=0.73 (8 km); Calientes1 r=0.68 (13 km); Chalsos r=0.62 (16 km)
#
# == RH_Avg
# G1 (6), r medio 0.95: Alto_Tala, Camp_Quellaveco, Charaque, Dique_pie_botadero, Tala-1, Tala_Legal
# G2 (5), r medio 0.74: Calacaja, Calientes1, Chalsos, Cortadera, DME3_Cortadera
# G3 (4), r medio 0.95: Altarani, Alto_Quellaveco, Minas_Sur, Sarallenque_MQG-15-02
# G4 (4), r medio 0.90: Apacheta, Cerro_Salviani, Papujune, Planta_Concentradora
# G5 (3), r medio 0.92: Camp_Quellaveco, Chancado_primario, Dique_pie_botadero
# G6 (3), r medio 0.90: Huachunta, Titire, Vizcachas
#
# Minas_Sur              mediana   35.8 -> Alto_Quellaveco r=0.98 (1 km); Altarani r=0.97 (1 km); Sarallenque_MQG-15-02 r=0.97 (4 km)
# Alto_Quellaveco        mediana   36.0 -> Minas_Sur r=0.98 (1 km); Sarallenque_MQG-15-02 r=0.92 (5 km); Altarani r=0.92 (2 km)
# Alto_Tala              mediana   36.3 -> Tala-1 r=0.97 (1 km); Tala_Legal r=0.97 (1 km); Dique_pie_botadero r=0.96 (1 km)
# Camp_Quellaveco        mediana   37.1 -> Charaque r=0.95 (3 km); Tala-1 r=0.95 (4 km); Minas_Sur r=0.94 (3 km)
# Cortadera              mediana   37.5 -> Chalsos r=0.89 (4 km); Cerro_Salviani r=0.89 (6 km); Apacheta r=0.85 (4 km)
# Dique_pie_botadero     mediana   37.6 -> Tala_Legal r=0.96 (2 km); Tala-1 r=0.96 (1 km); Alto_Tala r=0.96 (1 km)
# Charaque               mediana   38.0 -> Tala-1 r=0.96 (2 km); Camp_Quellaveco r=0.95 (3 km); Minas_Sur r=0.95 (6 km)
# Planta_Concentradora   mediana   38.1 -> Papujune r=0.96 (2 km); Minas_Sur r=0.94 (5 km); Charaque r=0.92 (4 km)
# Tala-1                 mediana   38.1 -> Alto_Tala r=0.97 (1 km); Dique_pie_botadero r=0.96 (1 km); Charaque r=0.96 (2 km)
# Altarani               mediana   38.2 -> Minas_Sur r=0.97 (1 km); Charaque r=0.93 (6 km); Alto_Quellaveco r=0.92 (2 km)
# Apacheta               mediana   38.3 -> Papujune r=0.89 (7 km); Planta_Concentradora r=0.88 (6 km); Minas_Sur r=0.88 (8 km)
# Tala_Legal             mediana   38.6 -> Alto_Tala r=0.97 (1 km); Dique_pie_botadero r=0.96 (2 km); Tala-1 r=0.96 (2 km)
# Calacaja               mediana   39.1 -> DME3_Cortadera r=0.75 (8 km); Calientes1 r=0.62 (13 km); Chalsos r=0.55 (16 km)
# Cerro_Salviani         mediana   40.1 -> Papujune r=0.91 (2 km); Alto_Tala r=0.90 (4 km); Cortadera r=0.89 (6 km)
# Papujune               mediana   40.3 -> Planta_Concentradora r=0.96 (2 km); Charaque r=0.92 (4 km); Camp_Quellaveco r=0.92 (4 km)
# Calientes1             mediana   40.7 -> Tala_Legal r=0.87 (6 km); Dique_pie_botadero r=0.85 (7 km); Cortadera r=0.85 (6 km)
# Chancado_primario      mediana   41.1 -> Dique_pie_botadero r=0.92 (3 km); Camp_Quellaveco r=0.91 (1 km); Tala-1 r=0.91 (3 km)
# DME3_Cortadera         mediana   42.1 -> Calientes1 r=0.83 (7 km); Chalsos r=0.80 (8 km); Calacaja r=0.75 (8 km)
# Sarallenque_MQG-15-02  mediana   44.0 -> Minas_Sur r=0.97 (4 km); Alto_Quellaveco r=0.92 (5 km); Altarani r=0.91 (4 km)
# Chalsos                mediana   45.0 -> Cortadera r=0.89 (4 km); Calientes1 r=0.84 (10 km); Cerro_Salviani r=0.81 (10 km)
# Huachunta              mediana   63.1 -> Vizcachas r=0.93 (6 km); Titire r=0.87 (16 km); Minas_Sur r=0.56 (53 km)
# Vizcachas              mediana   63.2 -> Huachunta r=0.93 (6 km); Titire r=0.89 (11 km); Minas_Sur r=0.56 (59 km)
# Titire                 mediana   63.7 -> Vizcachas r=0.89 (11 km); Huachunta r=0.87 (16 km); Minas_Sur r=0.61 (65 km)
#
# == WS_ms_Avg — por régimen (coseno del ciclo diario del vector de viento), periodo 2025-09-24 → 2026-09-24
# G1 (6), cos medio 0.92: Alto_Tala, Camp_Quellaveco, Charaque, Cortadera, Minas_Sur, Tala-1
# G2 (5), cos medio 0.83: Altarani, Alto_Quellaveco, Calientes1, Planta_Concentradora, Tala_Legal
# G3 (5), cos medio 0.92: Apacheta, Cerro_Salviani, Chancado_primario, Papujune, Sarallenque_MQG-15-02
# G4 (3), cos medio 0.90: Huachunta, Titire, Vizcachas
# G5 (2), cos medio 0.70: Calacaja, DME3_Cortadera
#
# Cerro_Salviani         mediana    1.3 -> Apacheta cos=0.92 (6 km); Papujune cos=0.89 (2 km); Chancado_primario cos=0.89 (6 km)
# Chancado_primario      mediana    1.4 -> Apacheta cos=0.98 (8 km); Papujune cos=0.92 (4 km); Sarallenque_MQG-15-02 cos=0.90 (4 km)
# Camp_Quellaveco        mediana    1.5 -> Cortadera cos=0.89 (10 km); Alto_Quellaveco cos=0.87 (3 km); Calientes1 cos=0.86 (10 km)
# Vizcachas              mediana    1.8 -> Huachunta cos=0.94 (6 km); Titire cos=0.82 (11 km); Chancado_primario cos=0.73 (59 km)
# Huachunta              mediana    1.8 -> Vizcachas cos=0.94 (6 km); Titire cos=0.94 (16 km); Cerro_Salviani cos=0.72 (59 km)
# Papujune               mediana    1.8 -> Sarallenque_MQG-15-02 cos=0.99 (8 km); Charaque cos=0.94 (4 km); Cortadera cos=0.94 (7 km)
# Calacaja               mediana    1.8 -> DME3_Cortadera cos=0.70 (8 km); Chancado_primario cos=0.65 (23 km); Sarallenque_MQG-15-02 cos=0.59 (27 km)
# Titire                 mediana    1.9 -> Huachunta cos=0.94 (16 km); Vizcachas cos=0.82 (11 km); Camp_Quellaveco cos=0.62 (65 km)
# DME3_Cortadera         mediana    1.9 -> Chancado_primario cos=0.82 (16 km); Apacheta cos=0.76 (11 km); Calacaja cos=0.70 (8 km)
# Alto_Tala              mediana    1.9 -> Tala-1 cos=0.99 (1 km); Charaque cos=0.97 (3 km); Minas_Sur cos=0.96 (8 km)
# Apacheta               mediana    2.3 -> Chancado_primario cos=0.98 (8 km); Papujune cos=0.93 (7 km); Cerro_Salviani cos=0.92 (6 km)
# Planta_Concentradora   mediana    2.3 -> Tala_Legal cos=0.77 (4 km); Alto_Quellaveco cos=0.72 (5 km); Calientes1 cos=0.66 (7 km)
# Minas_Sur              mediana    2.5 -> Alto_Tala cos=0.96 (8 km); Calientes1 cos=0.95 (12 km); Charaque cos=0.95 (6 km)
# Alto_Quellaveco        mediana    2.5 -> Tala_Legal cos=0.98 (8 km); Calientes1 cos=0.95 (11 km); Minas_Sur cos=0.94 (1 km)
# Charaque               mediana    2.6 -> Cortadera cos=0.99 (11 km); Alto_Tala cos=0.97 (3 km); Tala-1 cos=0.96 (2 km)
# Tala_Legal             mediana    2.8 -> Alto_Quellaveco cos=0.98 (8 km); Calientes1 cos=0.96 (6 km); Minas_Sur cos=0.94 (8 km)
# Cortadera              mediana    2.9 -> Charaque cos=0.99 (11 km); Alto_Tala cos=0.96 (9 km); Tala-1 cos=0.95 (9 km)
# Sarallenque_MQG-15-02  mediana    2.9 -> Papujune cos=0.99 (8 km); Charaque cos=0.94 (4 km); Cortadera cos=0.94 (14 km)
# Altarani               mediana    3.2 -> Tala_Legal cos=0.92 (9 km); Alto_Quellaveco cos=0.90 (2 km); Calientes1 cos=0.87 (14 km)
# Calientes1             mediana    3.4 -> Tala_Legal cos=0.96 (6 km); Minas_Sur cos=0.95 (12 km); Alto_Quellaveco cos=0.95 (11 km)
# Tala-1                 mediana    3.4 -> Alto_Tala cos=0.99 (1 km); Charaque cos=0.96 (2 km); Cortadera cos=0.95 (9 km)
# Dique_pie_botadero     mediana    3.6 -> Camp_Quellaveco cos=0.75 (3 km); Cerro_Salviani cos=0.67 (4 km); Titire cos=0.59 (66 km)
# Sin pareja (parecido medio < 0.6), una figura cada una: Dique_pie_botadero
# Fuera del agrupamiento (stations.WIND_EXCLUDED), una figura cada una: Chalsos, Mina_Norte, Sarallenque
#
# == combinado (T, HR)
# G1 (6), r medio 0.90: Altarani, Alto_Tala, Camp_Quellaveco, Charaque, Dique_pie_botadero, Tala_Legal
# G2 (5), r medio 0.75: Calacaja, Calientes1, Chalsos, Cortadera, DME3_Cortadera
# G3 (3), r medio 0.93: Alto_Quellaveco, Minas_Sur, Sarallenque_MQG-15-02
# G4 (3), r medio 0.85: Alto_Tala, Cerro_Salviani, Papujune
# G5 (3), r medio 0.91: Apacheta, Papujune, Planta_Concentradora
# G6 (3), r medio 0.86: Camp_Quellaveco, Chancado_primario, Dique_pie_botadero
# G7 (3), r medio 0.86: Dique_pie_botadero, Minas_Sur, Tala-1
# G8 (3), r medio 0.91: Huachunta, Titire, Vizcachas

GROUPS: dict[str, list[list[str]]] = {
    'AirTC_Avg': [
        ['Altarani', 'Apacheta', 'Camp_Quellaveco', 'Charaque', 'Papujune', 'Planta_Concentradora'],
        ['Alto_Tala', 'Calientes1', 'Chalsos', 'Cortadera', 'Dique_pie_botadero', 'Tala_Legal'],
        ['Alto_Quellaveco', 'Cerro_Salviani', 'Minas_Sur', 'Sarallenque_MQG-15-02'],
        ['Calacaja', 'Calientes1', 'Chalsos', 'DME3_Cortadera'],
        ['Chancado_primario', 'Dique_pie_botadero', 'Tala_Legal'],
        ['Dique_pie_botadero', 'Minas_Sur', 'Tala-1'],
        ['Huachunta', 'Titire', 'Vizcachas'],
        ['Ilo'],
    ],
    'RH_Avg': [
        ['Alto_Tala', 'Camp_Quellaveco', 'Charaque', 'Dique_pie_botadero', 'Tala-1', 'Tala_Legal'],
        ['Calacaja', 'Calientes1', 'Chalsos', 'Cortadera', 'DME3_Cortadera'],
        ['Altarani', 'Alto_Quellaveco', 'Minas_Sur', 'Sarallenque_MQG-15-02'],
        ['Apacheta', 'Cerro_Salviani', 'Papujune', 'Planta_Concentradora'],
        ['Camp_Quellaveco', 'Chancado_primario', 'Dique_pie_botadero'],
        ['Huachunta', 'Titire', 'Vizcachas'],
        ['Ilo'],
    ],
    'WS_ms_Avg': [
        ['Alto_Tala', 'Camp_Quellaveco', 'Charaque', 'Cortadera', 'Minas_Sur', 'Tala-1'],
        ['Altarani', 'Alto_Quellaveco', 'Calientes1', 'Planta_Concentradora', 'Tala_Legal'],
        ['Apacheta', 'Cerro_Salviani', 'Chancado_primario', 'Papujune', 'Sarallenque_MQG-15-02'],
        ['Huachunta', 'Titire', 'Vizcachas'],
        ['Calacaja', 'DME3_Cortadera'],
        ['Dique_pie_botadero'],
        ['Chalsos'],
        ['Mina_Norte'],
        ['Sarallenque'],
        ['Ilo'],
    ],
}

GROUPS_COMBINED: list[list[str]] = [
    ['Altarani', 'Alto_Tala', 'Camp_Quellaveco', 'Charaque', 'Dique_pie_botadero', 'Tala_Legal'],
    ['Calacaja', 'Calientes1', 'Chalsos', 'Cortadera', 'DME3_Cortadera'],
    ['Alto_Quellaveco', 'Minas_Sur', 'Sarallenque_MQG-15-02'],
    ['Alto_Tala', 'Cerro_Salviani', 'Papujune'],
    ['Apacheta', 'Papujune', 'Planta_Concentradora'],
    ['Camp_Quellaveco', 'Chancado_primario', 'Dique_pie_botadero'],
    ['Dique_pie_botadero', 'Minas_Sur', 'Tala-1'],
    ['Huachunta', 'Titire', 'Vizcachas'],
    ['Ilo'],
]
