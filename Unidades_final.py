import arcpy
import logging

# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def obtener_capa_por_indice(indice_capa):
    mxd = arcpy.mp.ArcGISProject("CURRENT")
    mapa_activo = mxd.activeMap
    capas = mapa_activo.listLayers()
    if 0 <= indice_capa < len(capas):
        return capas[indice_capa]
    else:
        return None

def calcular_cubrimiento(geom_unidad, geom_construccion):
    interseccion = geom_unidad.intersect(geom_construccion, 4)
    area_interseccion = interseccion.area
    area_unidad = geom_unidad.area
    return (area_interseccion / area_unidad) * 100

def validate_units_attributes(units_layer, lands_layer, construccion_layer):
    if not units_layer or not lands_layer or not construccion_layer:
        logging.error("Una o más capas no se pudieron obtener.")
        return

    try:
        lands_data = {row[1]: row[2] for row in arcpy.da.SearchCursor(lands_layer, ["OBJECTID", "codigo", "fmi_"])}
        construccion_data = {row[0]: row[1] for row in arcpy.da.SearchCursor(construccion_layer, ["pk_constru", "SHAPE@"])}

        workspace = arcpy.Describe(units_layer).path
        edit = arcpy.da.Editor(workspace)
        edit.startEditing(False, True)
        edit.startOperation()

        with arcpy.da.UpdateCursor(units_layer, [
            "codigo", "npn_", "pk_construcciones", "folio", "fmi_", 
            "act_tipo_construccion", "act_tipo_de_dominio", "act_altura", 
            "act_planta", "act_tipo_unidad_construccion", "act_total_plantas_unidad", 
            "act_anio_construccion", "act_tipo_planta", "act_puntaje_noconvencional", "SHAPE@"
        ]) as cursor:
            cambios_realizados = False
            for row in cursor:
                errors = []
                updates = []

                if row[0] not in lands_data:
                    valid_land_code = next(iter(lands_data.keys()), None)
                    if valid_land_code and row[0] != valid_land_code:
                        row[0] = valid_land_code
                        updates.append(f"codigo actualizado con un codigo de terreno valido: {valid_land_code}")
                    elif not valid_land_code:
                        errors.append(f"codigo {row[0]} no coincide con ningun codigo en las entidades seleccionadas de lands_layer y no se encontro un reemplazo valido")

                if not row[1] or row[1] != row[0]:
                    row[1] = row[0]
                    updates.append(f"npn_ actualizado para coincidir con codigo: {row[0]}")

                geom_unidad = row[14]
                for pk_constru, geom_construccion in construccion_data.items():
                    cubrimiento = calcular_cubrimiento(geom_unidad, geom_construccion)
                    if cubrimiento > 90:
                        if not row[2] or row[2] != pk_constru:
                            row[2] = pk_constru
                            updates.append(f"pk_construcciones actualizado para coincidir con pk_constru de Construccion: {pk_constru}")
                        break

                if row[0] in lands_data:
                    land_fmi = lands_data[row[0]]
                    if land_fmi and (not row[3] or row[3] != land_fmi):
                        row[3] = land_fmi
                        updates.append(f"folio actualizado para coincidir con fmi_ de Terrenos: {land_fmi}")

                if not row[4] or row[4] != row[3]:
                    row[4] = row[3]
                    updates.append(f"fmi_ actualizado para coincidir con folio: {row[3]}")

                if row[5] is None or not isinstance(row[5], int):
                    errors.append("act_tipo_construccion no debe estar vacio y debe ser un entero")

                if row[6] is None or not isinstance(row[6], int):
                    errors.append("act_tipo_dominio no debe estar vacio y debe ser un entero")

                if row[7] != 3:
                    row[7] = 3
                    updates.append("act_altura actualizado a 3")

                if row[8] is None or not isinstance(row[8], int):
                    errors.append("act_planta no debe estar vacio y debe ser un entero")

                if row[9] is None or not isinstance(row[9], int):
                    errors.append("act_tipo_unidad_construccion no debe estar vacio y debe ser un entero")

                if row[10] is None or row[10] <= 0:
                    errors.append("act_total_plantas_unidad no debe estar vacio y debe ser mayor a 0")

                if row[11] is None or not isinstance(row[11], int):
                    errors.append("act_anio_construccion no debe estar vacio y debe ser un entero")

                if row[12] is None or not isinstance(row[12], int):
                    errors.append("act_tipo_planta no debe estar vacio y debe ser un entero")

                if updates:
                    logging.info("Actualizaciones:")
                    for update in updates:
                        logging.info(f" - {update}")
                    cursor.updateRow(row)
                    cambios_realizados = True

                if errors:
                    logging.error("Errores:")
                    for error in errors:
                        logging.error(f" - {error}")
                    cambios_realizados = True

            if not cambios_realizados:
                logging.info("Todos los atributos se encuentran debidamente llenos y no se produjeron cambios.")

        edit.stopOperation()
        decision = input("Validacion completada. ¿Desea confirmar los cambios? (si/no): ").strip().lower()
        if decision == 'si':
            edit.stopEditing(True)
            logging.info("Los cambios han sido confirmados.")
        else:
            edit.stopEditing(False)
            logging.info("Los cambios han sido abortados.")
    except Exception as e:
        edit.stopOperation()
        edit.stopEditing(False)
        logging.error(f"Ocurrio un error: {e}. Los cambios han sido abortados.")

units_layer = obtener_capa_por_indice(1)
lands_layer = obtener_capa_por_indice(2)
construccion_layer = obtener_capa_por_indice(0)

validate_units_attributes(units_layer, lands_layer, construccion_layer)


