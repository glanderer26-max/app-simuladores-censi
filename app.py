import streamlit as st
import psycopg2
import pandas as pd
from datetime import datetime

# Configuración de la página
st.set_page_config(page_title="CENSI - Simuladores", layout="wide")

# CONEXIÓN A LA NUBE (SUPABASE)
def conectar():
    return psycopg2.connect("postgresql://postgres.wiqsnrmbciciuopvpndb:USMPcscs1234$@aws-1-us-east-1.pooler.supabase.com:5432/postgres")

# --- MENÚ LATERAL ---
st.sidebar.title("Navegación")
opcion = st.sidebar.radio("Ir a:", ["📝 Registrar Uso", "📊 Ver Historial", "⚙️ Estado y Desgaste"])

conn = conectar()

try:
    if opcion == "📝 Registrar Uso":
        st.title("🏥 Registro de Uso - Simuladores")
        
        fecha_curso = st.date_input("📅 Selecciona la fecha del curso:", format="DD/MM/YYYY")
        st.write("---")
        st.write("Selecciona los datos del curso:")

        # 1. Nivel: TIPOS
        tipos_df = pd.read_sql('SELECT * FROM "Tipos"', conn)
        tipo_sel = st.selectbox("1. Selecciona el Tipo:", tipos_df['nombre_tipo'])
        id_tipo = tipos_df[tipos_df['nombre_tipo'] == tipo_sel]['id_tipo'].values[0]

        # 2. Nivel: CURSOS
        cursos_df = pd.read_sql(f'SELECT * FROM "Cursos" WHERE id_tipo = {id_tipo}', conn)
        if not cursos_df.empty:
            curso_sel = st.selectbox("2. Selecciona el Curso:", cursos_df['nombre_curso'])
            id_curso = cursos_df[cursos_df['nombre_curso'] == curso_sel]['id_curso'].values[0]

            # Cargar todos los simuladores
            sims_df = pd.read_sql('SELECT * FROM "Simuladores"', conn)

            # 3. Nivel: CASOS
            casos_df = pd.read_sql(f'SELECT * FROM "Casos" WHERE id_curso = {id_curso}', conn)
            
            if not casos_df.empty:
                
                # =======================================================
                # LÓGICA MASIVA PARA: AMLS, CASOS CLINICOS, ECOEs
                # =======================================================
                cursos_masivos = [
                    "AMLS", "CASOS CLINICOS", "CASOS CLÍNICOS", "ECOE EMyT", 
                    "ECOE FOE", "ECOE Obstetricia", "ECOE Enfermeria", "ECOE Enfermería"
                ]
                
                if curso_sel in cursos_masivos:
                    st.write("---")
                    st.subheader(f"📋 Asignación Masiva por Casos ({curso_sel})")
                    st.info("💡 Asigna un simulador avanzado a cada caso. Si un caso o estación no se realizó, déjalo en '(No usar)'.")
                    
                    avanzados_df = sims_df[~sims_df['nombre_equipo'].str.contains('Laerdal|Prestan', case=False, na=False)]
                    if 'marca' in avanzados_df.columns:
                        avanzados_df = avanzados_df[~avanzados_df['marca'].str.contains('Laerdal|Prestan', case=False, na=False)]
                    
                    if avanzados_df.empty:
                        st.warning("⚠️ No se encontraron equipos avanzados registrados.")
                        opciones_sims = ["(No usar)"]
                    else:
                        opciones_sims = ["(No usar)"] + avanzados_df['nombre_equipo'].tolist()
                    
                    selecciones_masivas = {}
                    st.write("") 
                    
                    for index, row in casos_df.iterrows():
                        col1, col2 = st.columns([2, 3])
                        with col1:
                            st.markdown(f"**🩺 {row['nombre_caso']}**")
                        with col2:
                            sel = st.selectbox("Simulador", opciones_sims, key=f"masivo_sim_{row['id_caso']}", label_visibility="collapsed")
                            if sel != "(No usar)":
                                selecciones_masivas[row['id_caso']] = sel

                    st.write("---")
                    observaciones = st.text_area("Observaciones de mantenimiento (opcional):")

                    if st.button(f"Guardar Registros {curso_sel}"):
                        if not selecciones_masivas:
                            st.warning("⚠️ Debes asignar al menos un simulador a un caso antes de guardar.")
                        else:
                            cursor = conn.cursor()
                            query = 'INSERT INTO "Historial_Uso" (fecha, id_tipo, id_curso, id_caso, id_simulador, observaciones) VALUES (%s, %s, %s, %s, %s, %s)'
                            
                            for id_caso_iter, nombre_sim in selecciones_masivas.items():
                                id_sim = sims_df[sims_df['nombre_equipo'] == nombre_sim]['id_simulador'].values[0]
                                cursor.execute(query, (str(fecha_curso), int(id_tipo), int(id_curso), int(id_caso_iter), int(id_sim), observaciones))
                            
                            conn.commit()
                            st.success(f"✅ ¡Éxito! Se guardaron {len(selecciones_masivas)} registros en la nube para {curso_sel}.")

                # =======================================================
                # LÓGICA PARA EL RESTO DE LOS CURSOS (Individual)
                # =======================================================
                else:
                    caso_sel = st.selectbox("3. Selecciona el Caso:", casos_df['nombre_caso'])
                    id_caso = casos_df[casos_df['nombre_caso'] == caso_sel]['id_caso'].values[0]

                    st.write("---")
                    
                    if curso_sel == "BLS":
                        st.subheader("🛠️ Selección Múltiple de Equipos (BLS)")
                        num_sims = st.number_input("¿Cuántos simuladores de CADA TIPO necesitas?", min_value=1, max_value=20, value=3)
                        col1, col2 = st.columns(2)
                        adultos_df = sims_df[sims_df['nombre_equipo'].str.contains('Adult', case=False, na=False) | sims_df['modelo'].str.contains('Adult', case=False, na=False)]
                        neonatos_df = sims_df[sims_df['nombre_equipo'].str.contains('Neonat|Lactante|Bebe', case=False, na=False) | sims_df['modelo'].str.contains('Neonat', case=False, na=False)]
                        if adultos_df.empty: adultos_df = sims_df
                        if neonatos_df.empty: neonatos_df = sims_df

                        with col1:
                            st.markdown("🧑 **Simuladores Adultos**")
                            sel_adultos = st.multiselect(f"Elige hasta {num_sims}:", adultos_df['nombre_equipo'], max_selections=num_sims)
                        with col2:
                            st.markdown("👶 **Simuladores Neonatales**")
                            sel_neonatos = st.multiselect(f"Elige hasta {num_sims}:", neonatos_df['nombre_equipo'], max_selections=num_sims)
                        simuladores_finales = sel_adultos + sel_neonatos

                    elif curso_sel == "ACLS":
                        st.subheader("🛠️ Selección de Equipos (ACLS)")
                        st.markdown("🧑 **1. Fase Inicial: Soporte Básico**")
                        num_adultos = st.number_input("¿Cuántos simuladores básicos de Adulto necesitas?", min_value=1, max_value=20, value=2)
                        adultos_df = sims_df[sims_df['nombre_equipo'].str.contains('Adult', case=False, na=False) | sims_df['modelo'].str.contains('Adult', case=False, na=False)]
                        if adultos_df.empty: adultos_df = sims_df
                        sel_adultos_acls = st.multiselect(f"Elige hasta {num_adultos} simuladores básicos:", adultos_df['nombre_equipo'], max_selections=num_adultos)
                        
                        st.write("") 
                        st.markdown("🫀 **2. Escenarios: Simulador Avanzado**")
                        avanzados_df = sims_df[~sims_df['nombre_equipo'].str.contains('Laerdal|Prestan|Adulto', case=False, na=False)]
                        if 'marca' in avanzados_df.columns:
                            avanzados_df = avanzados_df[~avanzados_df['marca'].str.contains('Laerdal|Prestan', case=False, na=False)]
                        if avanzados_df.empty:
                            st.warning("⚠️ No se encontraron equipos avanzados.")
                            sel_avanzado = None
                        else:
                            sel_avanzado = st.selectbox("Selecciona el simulador avanzado a usar (Solo 1):", avanzados_df['nombre_equipo'])
                        simuladores_finales = sel_adultos_acls.copy()
                        if sel_avanzado: simuladores_finales.append(sel_avanzado)

                    elif curso_sel == "PALS":
                        st.subheader("🛠️ Selección de Equipos (PALS)")
                        st.markdown("👶 **1. Fase Inicial: Soporte Básico**")
                        num_basicos_pals = st.number_input("¿Cuántos simuladores básicos de CADA TIPO necesitas?", min_value=1, max_value=20, value=2, key="num_pals")
                        col_pals1, col_pals2 = st.columns(2)
                        infantes_basicos_df = sims_df[sims_df['nombre_equipo'].str.contains('Infante|Niño|Pediatric', case=False, na=False) | sims_df['modelo'].str.contains('Infante', case=False, na=False)]
                        neonatos_basicos_df = sims_df[sims_df['nombre_equipo'].str.contains('Neonat|Bebe|Lactante', case=False, na=False) | sims_df['modelo'].str.contains('Neonat', case=False, na=False)]
                        if infantes_basicos_df.empty: infantes_basicos_df = sims_df
                        if neonatos_basicos_df.empty: neonatos_basicos_df = sims_df

                        with col_pals1:
                            st.markdown("👦 **Básicos: Infante (Prestan)**")
                            sel_infantes_basicos = st.multiselect(f"Elige hasta {num_basicos_pals}:", infantes_basicos_df['nombre_equipo'], max_selections=num_basicos_pals)
                        with col_pals2:
                            st.markdown("🍼 **Básicos: Neonato (Prestan)**")
                            sel_neonatos_basicos = st.multiselect(f"Elige hasta {num_basicos_pals}:", neonatos_basicos_df['nombre_equipo'], max_selections=num_basicos_pals)

                        st.write("---")
                        st.markdown("🫀 **2. Escenarios: Simuladores Avanzados**")
                        col_pals3, col_pals4 = st.columns(2)
                        pediasim_df = sims_df[sims_df['nombre_equipo'].str.contains('Pediasim', case=False, na=False) | sims_df['modelo'].str.contains('Pediasim', case=False, na=False)]
                        luna_df = sims_df[sims_df['nombre_equipo'].str.contains('Luna', case=False, na=False) | sims_df['modelo'].str.contains('Luna', case=False, na=False)]
                        if pediasim_df.empty: pediasim_df = sims_df
                        if luna_df.empty: luna_df = sims_df

                        with col_pals3:
                            st.markdown("👦 **Avanzado: Infante (Pediasim)**")
                            sel_pediasim = st.multiselect("Selecciona simuladores a usar:", pediasim_df['nombre_equipo'])
                        with col_pals4:
                            st.markdown("🍼 **Avanzado: Neonato (Luna)**")
                            sel_luna = st.multiselect("Selecciona simuladores a usar:", luna_df['nombre_equipo'])

                        simuladores_finales = sel_infantes_basicos + sel_neonatos_basicos + sel_pediasim + sel_luna

                    elif curso_sel == "SURVEY":
                        st.subheader("🛠️ Selección de Equipos por Grupos (SURVEY)")
                        num_grupos = st.number_input("¿Cuántos grupos de alumnos hay?", min_value=1, max_value=10, value=1)
                        avanzados_df = sims_df[~sims_df['nombre_equipo'].str.contains('Laerdal|Prestan', case=False, na=False)]
                        if 'marca' in avanzados_df.columns:
                            avanzados_df = avanzados_df[~avanzados_df['marca'].str.contains('Laerdal|Prestan', case=False, na=False)]
                        if avanzados_df.empty:
                            st.warning("⚠️ No se encontraron equipos avanzados.")
                            simuladores_finales = []
                        else:
                            st.markdown(f"🫀 **Simuladores Avanzados**")
                            simuladores_finales = st.multiselect(f"Selecciona hasta {num_grupos} simulador(es):", avanzados_df['nombre_equipo'], max_selections=num_grupos)

                    else:
                        st.subheader("🛠️ Selección de Equipos")
                        simuladores_finales = st.multiselect(f"Selecciona todos los simuladores a usar:", sims_df['nombre_equipo'])

                    observaciones = st.text_area("Observaciones de mantenimiento (opcional):")

                    if st.button("Guardar Registro"):
                        if len(simuladores_finales) == 0:
                            st.warning("⚠️ Selecciona al menos un simulador antes de guardar.")
                        else:
                            cursor = conn.cursor()
                            query = 'INSERT INTO "Historial_Uso" (fecha, id_tipo, id_curso, id_caso, id_simulador, observaciones) VALUES (%s, %s, %s, %s, %s, %s)'
                            
                            for nombre_sim in simuladores_finales:
                                id_sim = sims_df[sims_df['nombre_equipo'] == nombre_sim]['id_simulador'].values[0]
                                cursor.execute(query, (str(fecha_curso), int(id_tipo), int(id_curso), int(id_caso), int(id_sim), observaciones))
                            
                            conn.commit()
                            st.success(f"✅ ¡Éxito! Se registraron {len(simuladores_finales)} equipos en la nube.")

            else:
                st.warning("No hay casos registrados para este curso.")
        else:
            st.warning("No hay cursos registrados para este tipo.")

    # ==========================================
    # PESTAÑA 2: VER HISTORIAL
    # ==========================================
    elif opcion == "📊 Ver Historial":
        st.title("📊 Historial Interactivo de Uso")
        st.info("💡 **Conectado a la Nube:** Cualquier cambio aquí se guardará directamente en Supabase.")
        
        query_historial = """
        SELECT 
            h.id_registro AS "ID",
            h.fecha AS "Fecha",
            t.nombre_tipo AS "Tipo",
            c.nombre_curso AS "Curso",
            ca.nombre_caso AS "Caso",
            s.nombre_equipo AS "Simulador",
            h.observaciones AS "Observaciones"
        FROM "Historial_Uso" h
        JOIN "Tipos" t ON h.id_tipo = t.id_tipo
        JOIN "Cursos" c ON h.id_curso = c.id_curso
        JOIN "Casos" ca ON h.id_caso = ca.id_caso
        JOIN "Simuladores" s ON h.id_simulador = s.id_simulador
        ORDER BY h.fecha DESC
        """
        
        historial_df = pd.read_sql(query_historial, conn)
        
        if not historial_df.empty:
            historial_df['Fecha'] = pd.to_datetime(historial_df['Fecha'].astype(str).str[:10])
            historial_df['Observaciones'] = historial_df['Observaciones'].fillna("")
            
            edited_df = st.data_editor(
                historial_df,
                column_config={"Fecha": st.column_config.DateColumn("Fecha", format="DD/MM/YYYY")},
                disabled=["ID", "Tipo", "Curso", "Caso", "Simulador"], 
                num_rows="dynamic",
                use_container_width=True,
                key="editor_historial"
            )
            
            if st.button("💾 Guardar Cambios"):
                cursor = conn.cursor()
                cambios = 0
                
                ids_originales = set(historial_df['ID'])
                ids_editados = set(edited_df['ID'])
                ids_eliminados = ids_originales - ids_editados
                
                # Eliminar en la Nube
                for id_elim in ids_eliminados:
                    cursor.execute('DELETE FROM "Historial_Uso" WHERE id_registro = %s', (int(id_elim),))
                    cambios += 1
                
                # Actualizar en la Nube
                for index, row in edited_df.iterrows():
                    id_actual = int(row['ID'])
                    if id_actual in ids_originales:
                        fila_orig = historial_df[historial_df['ID'] == id_actual].iloc[0]
                        if row['Fecha'] != fila_orig['Fecha'] or row['Observaciones'] != fila_orig['Observaciones']:
                            fecha_sql = row['Fecha'].strftime('%Y-%m-%d') if pd.notnull(row['Fecha']) else None
                            cursor.execute(
                                'UPDATE "Historial_Uso" SET fecha = %s, observaciones = %s WHERE id_registro = %s', 
                                (fecha_sql, str(row['Observaciones']), id_actual)
                            )
                            cambios += 1
                
                if cambios > 0:
                    conn.commit()
                    st.success(f"✅ ¡Se guardaron {cambios} modificación(es) en la nube!")
                    st.rerun() 
                else:
                    st.info("No se detectaron cambios.")
            
            st.write("---")
            csv_df = historial_df.copy()
            csv_df['Fecha'] = csv_df['Fecha'].dt.strftime('%d/%m/%Y')
            csv = csv_df.to_csv(index=False).encode('utf-8')
            st.download_button(label="📥 Descargar CSV", data=csv, file_name='historial_nube.csv', mime='text/csv')
        else:
            st.info("Aún no hay registros.")

    # ==========================================
    # PESTAÑA 3: ESTADO Y DESGASTE
    # ==========================================
    elif opcion == "⚙️ Estado y Desgaste":
        st.title("⚙️ Estado y Desgaste de Simuladores")
        st.info("💡 Calculando métricas en tiempo real desde Supabase.")
        
        # Postgres usa COALESCE en lugar de IFNULL
        query_desgaste = """
        SELECT 
            s.nombre_equipo AS "Simulador",
            COUNT(h.id_registro) AS "Clases_Impartidas",
            SUM(COALESCE(c.duracion_minutos, 0)) AS "Minutos_Totales",
            SUM(COALESCE(c.compresiones_min, 0)) AS "Compresiones_Totales",
            SUM(COALESCE(c.ventilaciones_min, 0)) AS "Ventilaciones_Totales",
            SUM(COALESCE(c.frecuencia_cardiaca, 0) * COALESCE(c.duracion_minutos, 0)) AS "Latidos_Totales",
            SUM(COALESCE(c.frecuencia_respiratoria, 0) * COALESCE(c.duracion_minutos, 0)) AS "Respiraciones_Totales"
        FROM "Historial_Uso" h
        JOIN "Simuladores" s ON h.id_simulador = s.id_simulador
        JOIN "Casos" c ON h.id_caso = c.id_caso
        GROUP BY s.id_simulador, s.nombre_equipo
        ORDER BY "Minutos_Totales" DESC
        """
        
        try:
            desgaste_df = pd.read_sql(query_desgaste, conn)
            
            if not desgaste_df.empty:
                st.dataframe(desgaste_df, use_container_width=True)
                st.write("---")
                col1, col2 = st.columns(2)
                with col1:
                    st.write("**Top Minutos de Uso**")
                    st.bar_chart(desgaste_df.set_index("Simulador")["Minutos_Totales"])
                with col2:
                    st.write("**Top Desgaste de Resorte (Compresiones)**")
                    df_compresiones = desgaste_df[desgaste_df["Compresiones_Totales"] > 0]
                    if not df_compresiones.empty:
                        st.bar_chart(df_compresiones.set_index("Simulador")["Compresiones_Totales"], color="#ff4b4b")
                    else:
                        st.write("Sin registros de compresiones.")
            else:
                st.info("No hay registros suficientes.")
                
        except Exception as e:
            st.error(f"Error calculando desgaste: {e}")

except Exception as e:
    st.error(f"Ocurrió un error: {e}")

finally:
    if conn:
        conn.close()