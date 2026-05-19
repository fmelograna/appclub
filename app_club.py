import streamlit as st
from supabase import create_client, Client
import pandas as pd
from datetime import datetime

# --- 1. CONFIGURACIÓN Y CONEXIÓN A LA NUBE ---
# ⚠️ REEMPLAZÁ ESTOS DATOS CON LOS DE TU PANEL DE SUPABASE:
SUPABASE_URL = "https://rgvixnnaedevjkfzrtsp.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InJndml4bm5hZWRldmprZnpydHNwIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzkxMzY0MTksImV4cCI6MjA5NDcxMjQxOX0.q5NeRcDiGRwfoDaQe0pYMOV3D--zz2Ox-pOhL-AS3iQ"

@st.cache_resource
def conectar_supabase() -> Client:
    return create_client(SUPABASE_URL, SUPABASE_KEY)

# --- 2. FUNCIONES DE LÓGICA CON SUPABASE ---
def registrar_socio_completo(id_s, nombre, actividades, monto_especial=None):
    supabase = conectar_supabase()
    try:
        monto = float(monto_especial) if monto_especial is not None else None
        supabase.table("socios").insert({"id": int(id_s), "nombre": nombre, "monto_especial": monto}).execute()
        
        for act in actividades:
            supabase.table("socio_actividades").insert({"socio_id": int(id_s), "actividad": act}).execute()
        return True
    except:
        return False

def generar_cuotas_inteligentes(mes, precios_actividades):
    supabase = conectar_supabase()
    try:
        todos_socios = supabase.table("socios").select("id, monto_especial").execute().data
        count = 0
        
        for s in todos_socios:
            socio_id = s["id"]
            monto_especial = s["monto_especial"]
            
            existe = supabase.table("cuotas").select("id").eq("socio_id", socio_id).eq("mes", mes).execute().data
            if existe:
                continue
                
            if monto_especial is not None:
                monto_final = monto_especial
            else:
                deportes = supabase.table("socio_actividades").select("actividad").eq("socio_id", socio_id).execute().data
                monto_final = sum(precios_actividades.get(d["actividad"], 0.0) for d in deportes)
                
            supabase.table("cuotas").insert({"socio_id": socio_id, "mes": mes, "monto": float(monto_final), "pagada": 0}).execute()
            count += 1
        return count
    except:
        return 0

def pagar_cuota(cuota_id):
    supabase = conectar_supabase()
    supabase.table("cuotas").update({"pagada": 1}).eq("id", int(cuota_id)).execute()

# --- 3. INTERFAZ VISUAL ---
st.set_page_config(page_title="Sistema Club Central", layout="wide")

LISTA_ACTIVIDADES = ["Futbol", "Voley", "Patin", "Basquet"]
MESES = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]

if "autenticado" not in st.session_state:
    st.session_state.autenticado = False

st.sidebar.title("🔑 Ingreso al Sistema")
if not st.session_state.autenticado:
    usuario = st.sidebar.text_input("Usuario")
    contrasenia = st.sidebar.text_input("Contraseña", type="password")
    if st.sidebar.button("Iniciar Sesión", use_container_width=True):
        if usuario == "admin" and contrasenia == "club123":
            st.session_state.autenticado = True
            st.session_state.pagina = "panel"
            st.rerun()
        else:
            st.sidebar.error("❌ Credenciales incorrectas")
    st.warning("Iniciá sesión para administrar el club.")
    st.stop()

if "pagina" not in st.session_state:
    st.session_state.pagina = "panel"

st.sidebar.title("🏆 Club Central")
if st.sidebar.button("Cerrar Sesión", type="secondary", use_container_width=True):
    st.session_state.autenticado = False
    st.rerun()

st.sidebar.markdown("---")
if st.sidebar.button("📊 Panel General", use_container_width=True, type="primary" if st.session_state.pagina == "panel" else "secondary", key="nav_panel"):
    st.session_state.pagina = "panel"
    st.rerun()
if st.sidebar.button("👤 Gestión de Socios", use_container_width=True, type="primary" if st.session_state.pagina == "socios" else "secondary", key="nav_socios"):
    st.session_state.pagina = "socios"
    st.rerun()
if st.sidebar.button("💰 Caja y Cobranzas", use_container_width=True, type="primary" if st.session_state.pagina == "caja" else "secondary", key="nav_caja"):
    st.session_state.pagina = "caja"
    st.rerun()
if st.sidebar.button("⚙️ Administración", use_container_width=True, type="primary" if st.session_state.pagina == "admin" else "secondary", key="nav_admin"):
    st.session_state.pagina = "admin"
    st.rerun()

# --- PANEL GENERAL ---
if st.session_state.pagina == "panel":
    st.subheader("Estado de Cuentas e Ingresos")
    mes_balance = st.selectbox("Seleccione mes para ver balance:", MESES, index=datetime.now().month - 1, key="sel_mes_balance")
    
    supabase = conectar_supabase()
    
    try:
        res_ingresos = supabase.table("cuotas").select("monto").eq("mes", mes_balance).eq("pagada", 1).execute().data
        total_recaudado = sum(r["monto"] for r in res_ingresos) if res_ingresos else 0.0
        
        raw_socios = supabase.table("socios").select("id, nombre, monto_especial").execute().data
        raw_actividades = supabase.table("socio_actividades").select("socio_id, actividad").execute().data
        raw_cuotas = supabase.table("cuotas").select("socio_id, pagada").execute().data
        
        df_list = []
        for s in raw_socios:
            s_id = s["id"]
            s_acts = [a["actividad"] for a in raw_actividades if a["socio_id"] == s_id]
            acts_str = ", ".join(s_acts) if s_acts else "Sin Actividad"
            tipo = "⭐ Arancel Especial" if s["monto_especial"] is not None else "Común"
            pendientes = sum(1 for c in raw_cuotas if c["socio_id"] == s_id and c["pagada"] == 0)
            
            df_list.append({"ID": s_id, "Nombre": s["nombre"], "Actividades": acts_str, "Tipo Arancel": tipo, "Cuotas Pendientes": pendientes})
            
        df = pd.DataFrame(df_list)

        c1, c2, c3, c4 = st.columns(4)
        if not df.empty:
            c1.metric("Total Socios", len(df))
            morosos = len(df[df['Cuotas Pendientes'] > 0])
            c2.metric("Morosos", morosos)
            with c2:
                if morosos > 0:
                    if st.button("🔍 Ir a cobrar", type="secondary", key="btn_ir_a_cobrar_seguro"):
                        st.session_state.pagina = "caja"
                        st.rerun()
            c3.metric("Al día", len(df) - morosos)
        else:
            c1.metric("Total Socios", 0)
            c2.metric("Morosos", 0)
            c3.metric("Al día", 0)
        c4.metric(f"💰 Recaudación {mes_balance}", f"${total_recaudado:,.2f}")

        st.markdown("---")
        st.write("### Listado General de Socios")
        if not df.empty:
            def resaltar_morosos(val):
                if isinstance(val, int) or isinstance(val, float):
                    return f"color: {'red' if val > 0 else 'green'}"
                return ''
            st.dataframe(df.style.map(resaltar_morosos, subset=['Cuotas Pendientes']), use_container_width=True, key="tabla_socios_view")
        else:
            st.info("Aún no hay socios en la base de datos.")
    except Exception as e:
        st.error("Asegurate de haber corrido las tablas de SQL en el panel de Supabase.")

# --- GESTIÓN DE SOCIOS ---
elif st.session_state.pagina == "socios":
    st.subheader("Carga de Miembros al Sistema")
    sub_tab1, sub_tab2 = st.tabs(["📝 Alta Regular / Multideporte", "🤝 Alta con Arancel Especial (Becas)"])
    
    with sub_tab1:
        with st.form("alta_regular", clear_on_submit=True):
            col1, col2 = st.columns(2)
            dni = col1.number_input("DNI / Nro Socio", min_value=1, step=1, key="reg_dni")
            nombre = col2.text_input("Nombre y Apellido", key="reg_nom")
            deportes = st.multiselect("Seleccione todas las actividades:", LISTA_ACTIVIDADES, key="reg_multisel_dep")
            
            if st.form_submit_button("Registrar Socio Multideporte"):
                if nombre and deportes:
                    if registrar_socio_completo(dni, nombre, deportes, None):
                        st.success(f"Socio {nombre} registrado con éxito.")
                        st.rerun()
                    else:
                        st.error("Error al registrar: Verificá que el DNI no exista.")
                else:
                    st.error("Complete los campos requeridos.")

    with sub_tab2:
        st.info("Socio con cuota fija cerrada o becas.")
        with st.form("alta_especial", clear_on_submit=True):
            col1, col2 = st.columns(2)
            dni_esp = col1.number_input("DNI / Nro Socio", min_value=1, step=1, key="esp_dni")
            nombre_esp = col2.text_input("Nombre y Apellido", key="esp_nom")
            deportes_esp = st.multiselect("Actividades:", LISTA_ACTIVIDADES, key="esp_multisel_dep")
            monto_pactado = st.number_input("Monto mensual ($):", min_value=0, value=4000, step=500, key="esp_monto")
            
            if st.form_submit_button("Registrar Socio Especial"):
                if nombre_esp and deportes_esp:
                    if registrar_socio_completo(dni_esp, nombre_esp, deportes_esp, monto_pactado):
                        st.success(f"¡Beneficio asignado a {nombre_esp}!")
                        st.rerun()
                    else:
                        st.error("Error al registrar: Verificá que el DNI no exista.")

# --- CAJA Y COBRANZAS ---
elif st.session_state.pagina == "caja":
    st.subheader("Módulo de Cobro - Listado de Socios Deudores")
    supabase = conectar_supabase()
    
    try:
        raw_cuotas_pendientes = supabase.table("cuotas").select("socio_id").eq("pagada", 0).execute().data
        
        if raw_cuotas_pendientes:
            ids_deudores = list(set([c["socio_id"] for c in raw_cuotas_pendientes]))
            raw_socios_deudores = supabase.table("socios").select("id, nombre").in_("id", ids_deudores).execute().data
            
            nombres_deudores = {f"{r['id']} - {r['nombre']}": r['id'] for r in raw_socios_deudores}
            st.info(f"⚠️ Actualmente hay {len(nombres_deudores)} socios con deudas pendientes.")
            seleccion = st.selectbox("Seleccione el socio deudor:", list(nombres_deudores.keys()), key="sel_socio_deudor")
            socio_id = nombres_deudores[seleccion]

            st.markdown("---")
            cuotas = supabase.table("cuotas").select("id, mes, monto").eq("socio_id", socio_id).eq("pagada", 0).execute().data
            
            if cuotas:
                st.write("### Cuotas pendientes de cobro:")
                for row in cuotas:
                    key_btn = f"pay_unique_{row['id']}_{row['mes']}"
                    c_mes, c_monto, c_estado, c_accion = st.columns(4)
                    c_mes.write(f"📅 **{row['mes']}**")
                    c_monto.write(f"${row['monto']:,.2f}")
                    c_estado.write("🔴 PENDIENTE")
                    if c_accion.button("Cobrar", key=key_btn):
                        pagar_cuota(row['id'])
                        st.toast(f"Cobro exitoso!")
                        st.rerun()
        else:
            st.balloons()
            st.success("😎 ¡Qué tranquilidad! No se registran deudas.")
    except Exception as e:
        st.error("Error de comunicación con Supabase.")

# --- ADMINISTRACIÓN ---
elif st.session_state.pagina == "admin":
    st.subheader("Generación Masiva de Cuotas Inteligentes")
    with st.form("config_cuotas"):
        mes_nombre = st.selectbox("Mes a facturar:", MESES, index=datetime.now().month - 1, key="admin_mes_gen")
        col_f, col_v = st.columns(2)
        p_futbol = col_f.number_input("Precio Fútbol ($)", min_value=0, value=12000, step=500, key="p_fut")
        p_voley = col_v.number_input("Precio Vóley ($)", min_value=0, value=9500, step=500, key="p_vol")
        col_p, col_b = st.columns(2)
        p_patin = col_p.number_input("Precio Patín ($)", min_value=0, value=11000, step=500, key="p_pat")
        p_basquet = col_b.number_input("Precio Básquet ($)", min_value=0, value=13000, step=500, key="p_bas")
        
        precios_map = {"Futbol": p_futbol, "Voley": p_voley, "Patin": p_patin, "Basquet": p_basquet}
        
        if st.form_submit_button("🚀 Generar y facturar mes"):
            procesados = generar_cuotas_inteligentes(mes_nombre, precios_map)
            if procesados > 0:
                st.success(f"¡Éxito! Se procesaron {procesados} liquidaciones.")
                st.rerun()
            else:
                st.warning("No se generaron cuotas nuevas para este periodo.")
