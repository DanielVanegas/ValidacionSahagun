import arcpy
from collections import defaultdict

def obtener_capa_por_indice(indice_capa):
    # Obtiene la capa por indice de la lista de capas del mapa activo
    mxd = arcpy.mp.ArcGISProject("CURRENT")
    mapa_activo = mxd.activeMap
    capas = mapa_activo.listLayers()
    if 0 <= indice_capa < len(capas):
        return capas[indice_capa]
    else:
        return None

def validate_constructions_attributes(constructions_layer, lands_layer):
    # Obtiene el codigo de la capa terrenos para comparacion
    lands_code = {row[0]: row[1] for row in arcpy.da.SearchCursor(lands_layer, ["OBJECTID", "codigo"])}
    
    # Inicia sesion de edicion
    workspace = arcpy.Describe(constructions_layer).path
    edit = arcpy.da.Editor(workspace)
    edit.startEditing(False, True)
    edit.startOperation()

    try:
        # Agrupar entidades por el atributo 'codigo'
        grouped_entities = defaultdict(list)
        with arcpy.da.SearchCursor(constructions_layer, ["OBJECTID", "codigo", "pk_constru"]) as cursor:
            for row in cursor:
                grouped_entities[row[1]].append(row[0])

        # El cursor ahora solo iterara sobre las entidades seleccionadas en constructions_layer
        with arcpy.da.UpdateCursor(constructions_layer, ["OBJECTID", "pk_constru", "codigo", "act_altura", "act_anio_c", 
                                                         "numero_mezanines", "numero_sotanos", "numero_semisotanos", 
                                                         "numero_pisos", "tipo_dominio", "terreno_codigo"]) as cursor:
            for row in cursor:
                errors = []
                updates = []

                # Regla 3: act_altura debe ser igual a 3
                if row[3] != 3:
                    row[3] = 3
                    updates.append("act_altura actualizado a 3")

                # Regla 4: act_anio_c no puede estar vacio
                if not row[4]:
                    errors.append("act_anio_c esta vacio")

                # Regla 5: Verificar cada atributo individualmente
                for i, attr in enumerate(["numero_mezanines", "numero_sotanos", "numero_semisotanos", "numero_pisos"], start=5):
                    if row[i] is None:
                        errors.append(f"{attr} esta vacio")

                # Regla 6: tipo_dominio no puede estar vacio
                if row[9] not in [0, 1]:
                    errors.append("tipo_dominio es invalido o esta vacio")

                # Regla 7 ajustada: Si el codigo no hace match, reemplazar por un codigo de terreno valido
                if row[2] not in lands_code.values():
                    valid_land_code = next(iter(lands_code.values()), None)
                    if valid_land_code is not None:
                        row[2] = valid_land_code
                        updates.append(f"codigo reemplazado con un codigo de terreno valido: {valid_land_code}")
                    else:
                        errors.append(f"codigo {row[2]} no coincide con ningun codigo en las entidades seleccionadas de lands_layer y no se encontro un reemplazo valido")

                # Regla 8: terreno_codigo no debe estar vacio y debe ser igual a codigo
                if not row[10] or row[10] != row[2]:
                    row[10] = row[2]
                    updates.append(f"terreno_codigo actualizado para coincidir con codigo: {row[2]}")

                # Regla 2: pk_constru no puede estar vacio y debe ser igual a codigo + secuencia
                if not row[1] or not row[1].startswith(row[2]):
                    codigo_base = row[2]
                    secuencia = grouped_entities[codigo_base].index(row[0]) + 1
                    pk_constru_nuevo = f"{codigo_base}{str(secuencia).zfill(3)}"
                    row[1] = pk_constru_nuevo
                    updates.append(f"pk_constru actualizado a {pk_constru_nuevo}")

                if errors:
                    print("Errores:")
                    for i, error in enumerate(errors, start=1):
                        print(f"{i}. {error}")

                if updates:
                    print("Actualizaciones:")
                    for update in updates:
                        print(f"- {update}")
                    cursor.updateRow(row)

        edit.stopOperation()
        print("Validacion completada.")
        decision = input("¿Desea confirmar los cambios? (si/no): ").strip().lower()
        if decision == 'si':
            edit.stopEditing(True)
            print("Los cambios han sido confirmados.")
        else:
            edit.stopEditing(False)
            print("Los cambios han sido abortados.")
    except Exception as e:
        edit.stopOperation()
        edit.stopEditing(False)
        print(f"Ocurrio un error: {e}. Los cambios han sido abortados.")

# Obtener capas
constructions_layer = obtener_capa_por_indice(0)
lands_layer = obtener_capa_por_indice(2)

# Asegurate de que las entidades esten seleccionadas en las capas antes de ejecutar
validate_constructions_attributes(constructions_layer, lands_layer)


