# app.py
import streamlit as st
import supabase_client as sc
import pandas as pd
import plotly.express as px
from datetime import datetime
import time

# --- Configuração da Página e CSS ---
st.set_page_config(
    page_title="Planner Financeiro",
    page_icon="💰",
    layout="wide"
)

# Função para carregar nosso CSS customizado
def load_css(file_name):
    try:
        with open(file_name) as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
    except FileNotFoundError:
        st.error(f"Arquivo CSS '{file_name}' não encontrado. Certifique-se que ele está na mesma pasta que app.py")

load_css("style.css")

# --- Categorias (Atualizadas) ---
CATEGORIAS_DESPESA = ['Moradia', 'Alimentação', 'Transporte', 'Lazer', 'Saúde', 'Outros']
CATEGORIAS_RECEITA = ['Salário', 'Freelance', 'Outros'] # 'Investimentos' saiu daqui
CATEGORIAS_INVESTIMENTO = ['Ações', 'Fundos Imobiliários', 'Renda Fixa', 'Cripto', 'Outros'] ### MUDANÇA ###

# --- Inicialização do Session State ---
if 'user' not in st.session_state:
    st.session_state['user'] = None

# --- Funções de Carregamento de Dados ---
@st.cache_data(ttl=300) # Cache por 5 minutos
def load_data(user_id):
    """Carrega transações e converte tipos."""
    transactions = sc.get_transactions(user_id)
    if transactions:
        df = pd.DataFrame(transactions)
        df['valor'] = pd.to_numeric(df['valor'])
        df['data'] = pd.to_datetime(df['data'])
        return df
    return pd.DataFrame(columns=['id', 'tipo', 'valor', 'descricao', 'categoria', 'data'])

# =========================================================================
# === PÁGINA 1: TELA DE LOGIN (Sem mudanças) ===============================
# =========================================================================
def show_login_page():
    st.title("💰 Bem-vindo ao seu Planner Financeiro")
    st.write("Faça login ou cadastre-se para continuar.")

    tab_login, tab_signup = st.tabs(["Login", "Cadastrar"])

    with tab_login:
        with st.form("login_form"):
            email_login = st.text_input("Email", key="login_email")
            password_login = st.text_input("Senha", type="password", key="login_pass")
            submitted_login = st.form_submit_button("Entrar")

            if submitted_login:
                response = sc.sign_in(email_login, password_login)
                if hasattr(response, 'user') and response.user:
                    st.session_state['user'] = response.user.model_dump()
                    st.success("Login realizado com sucesso!")
                    time.sleep(1) # Pequena pausa para o usuário ler a msg
                    st.rerun()
                else:
                    st.error(f"Erro no login: {response.get('error', 'Credenciais inválidas.')}")

    with tab_signup:
        with st.form("signup_form"):
            email_signup = st.text_input("Email", key="signup_email")
            password_signup = st.text_input("Senha", type="password", key="signup_pass")
            submitted_signup = st.form_submit_button("Cadastrar")

            if submitted_signup:
                if len(password_signup) < 6:
                    st.warning("A senha deve ter no mínimo 6 caracteres.")
                else:
                    response = sc.sign_up(email_signup, password_signup)
                    if hasattr(response, 'user') and response.user:
                        st.success("Cadastro realizado! Faça o login na aba ao lado.")
                    else:
                        st.error(f"Erro no cadastro: {response.get('error', 'Não foi possível cadastrar.')}")

# =========================================================================
# === PÁGINA 2: APLICAÇÃO PRINCIPAL (DASHBOARD) ==========================
# =========================================================================
def show_main_app():
    
    # --- Sidebar de Logout ---
    st.sidebar.write(f"Logado como: **{st.session_state['user']['email']}**")
    if st.sidebar.button("Logout"):
        response = sc.sign_out()
        if "error" not in response:
            st.session_state['user'] = None
            st.success("Logout realizado com sucesso!")
            time.sleep(1)
            st.rerun()
        else:
            st.error(f"Erro no logout: {response['error']}")

    # --- Carregar Dados ---
    user_id = st.session_state['user']['id']
    df = load_data(user_id) # Este é o DataFrame TOTAL

    # --- 1. HEADER E FILTROS ---
    with st.container(): # Container estilizado pelo CSS
        st.title("💰 Meu Planner Financeiro")
        
        if df.empty:
            st.info("Nenhuma transação encontrada. Adicione sua primeira transação abaixo!")
            ano_atual = datetime.now().year
            mes_atual = datetime.now().month
            df_filtered = df # Cria um dataframe vazio para não quebrar os KPIs mensais
        else:
            # Filtros de Mês e Ano (como no seu HTML)
            df['ano'] = df['data'].dt.year
            df['mes'] = df['data'].dt.month
            
            anos_disponiveis = sorted(df['ano'].unique(), reverse=True)
            meses_disponiveis = sorted(df['mes'].unique())
            
            ano_atual = datetime.now().year if datetime.now().year in anos_disponiveis else anos_disponiveis[0]
            mes_atual = datetime.now().month if datetime.now().month in meses_disponiveis else meses_disponiveis[0]

            col_filtro1, col_filtro2 = st.columns(2)
            ano_selecionado = col_filtro1.selectbox("Ano", anos_disponiveis, index=anos_disponiveis.index(ano_atual))
            mes_selecionado = col_filtro2.selectbox("Mês", meses_disponiveis, index=meses_disponiveis.index(mes_atual), 
                                                     format_func=lambda x: datetime(2020, x, 1).strftime('%B'))

            # Filtrar DataFrame para os KPIs MENSAIS e gráficos
            df_filtered = df[(df['ano'] == ano_selecionado) & (df['mes'] == mes_selecionado)]

    # --- 2. KPIs TOTAIS (Sem filtro de mês) ### MUDANÇA ### ---
    st.subheader("Visão Geral (Total)")
    receitas_total = df[df['tipo'] == 'receita']['valor'].sum()
    despesas_total = df[df['tipo'] == 'despesa']['valor'].sum()
    investimentos_total = df[df['tipo'] == 'investimento']['valor'].sum() ### MUDANÇA ###
    saldo_total = receitas_total - despesas_total

    col1, col2, col3, col4 = st.columns(4) ### MUDANÇA ###
    col1.metric("Receita Total", f"R$ {receitas_total:,.2f}")
    col2.metric("Despesa Total", f"R$ {despesas_total:,.2f}")
    col3.metric("Saldo Total", f"R$ {saldo_total:,.2f}")
    col4.metric("Investimentos (Reserva)", f"R$ {investimentos_total:,.2f}") ### MUDANÇA ###

    # --- 3. KPIs MENSAIS (Com filtro de mês) ### MUDANÇA ### ---
    st.subheader(f"Resumo de {datetime(2020, mes_selecionado, 1).strftime('%B')}/{ano_selecionado}")
    receitas_mes = df_filtered[df_filtered['tipo'] == 'receita']['valor'].sum()
    despesas_mes = df_filtered[df_filtered['tipo'] == 'despesa']['valor'].sum()
    investimentos_mes = df_filtered[df_filtered['tipo'] == 'investimento']['valor'].sum()
    saldo_mes = receitas_mes - despesas_mes

    col5, col6, col7, col8 = st.columns(4) ### MUDANÇA ###
    col5.metric("Receita do Mês", f"R$ {receitas_mes:,.2f}")
    col6.metric("Despesa do Mês", f"R$ {despesas_mes:,.2f}")
    col7.metric("Saldo do Mês", f"R$ {saldo_mes:,.2f}")
    col8.metric("Investimento do Mês", f"R$ {investimentos_mes:,.2f}") ### MUDANÇA ###

    st.markdown("---") # Separador visual

    # --- 4. CONTEÚDO PRINCIPAL (Transações e Gráficos) ---
    col_main, col_sidebar = st.columns([2, 1], gap="large") # 2fr 1fr como no seu HTML

    with col_main:
        # --- Formulário de Adição (como no seu HTML) ---
        with st.expander("📝 Adicionar Nova Transação", expanded=df.empty):
            
            # ### MUDANÇA ###: Seletor de TIPO movido para FORA do form
            # Isso força o rerun e permite que o seletor de Categoria mude dinamicamente
            tipo = st.selectbox("Tipo", ["despesa", "receita", "investimento"], key="add_tipo_selector")
            
            with st.form("add_form", clear_on_submit=True):
                col_form1, col_form2 = st.columns(2)
                with col_form1:
                    valor = st.number_input("Valor (R$)", min_value=0.01, format="%.2f", key="add_valor")
                    
                    # ### MUDANÇA ###: Lógica condicional para Categoria
                    if tipo == 'despesa':
                        categoria = st.selectbox("Categoria", CATEGORIAS_DESPESA, key="add_cat_des")
                    elif tipo == 'receita':
                        categoria = st.selectbox("Categoria", CATEGORIAS_RECEITA, key="add_cat_rec")
                    elif tipo == 'investimento':
                        categoria = st.selectbox("Categoria", CATEGORIAS_INVESTIMENTO, key="add_cat_inv")
                
                with col_form2:
                    data = st.date_input("Data", datetime.today(), key="add_data")
                    descricao = st.text_input("Descrição", placeholder="Ex: Salário, Aluguel, Ações...", key="add_desc")
                
                submitted_add = st.form_submit_button("Adicionar Transação")

                if submitted_add:
                    # 'tipo' já está definido (foi pego fora do form)
                    response = sc.add_transaction(user_id, tipo, valor, descricao, categoria, data)
                    if response:
                        st.success("Transação adicionada!")
                        st.cache_data.clear() # Limpa o cache para recarregar os dados
                        st.rerun()
                    else:
                        st.error("Falha ao adicionar transação.")

        # --- Histórico de Transações (como no seu HTML) ---
        with st.container(border=True):
            st.subheader(f"📊 Histórico de Transações de {datetime(2020, mes_selecionado, 1).strftime('%B')}")
            if df_filtered.empty:
                st.info("Nenhuma transação para este mês.")
            else:
                st.dataframe(
                    df_filtered[['data', 'descricao', 'categoria', 'tipo', 'valor']],
                    use_container_width=True,
                    hide_index=True
                )

    with col_sidebar:
        # --- Gráfico de Categorias (como no seu HTML) ---
        with st.container(border=True):
            st.subheader("🏷️ Despesas por Categoria")
            df_despesas = df_filtered[df_filtered['tipo'] == 'despesa']
            if not df_despesas.empty:
                fig_pie = px.pie(df_despesas, 
                                 names='categoria', 
                                 values='valor', 
                                 hole=.3) # Gráfico de rosca
                fig_pie.update_layout(legend_title_text='Categorias', margin=dict(t=0, b=0, l=0, r=0))
                st.plotly_chart(fig_pie, use_container_width=True)
            else:
                st.info("Nenhuma despesa registrada no período.")
        
        # --- ### MUDANÇA ###: Novo Gráfico de Investimentos ---
        with st.container(border=True):
            st.subheader("📈 Investimentos por Categoria")
            df_investimentos = df_filtered[df_filtered['tipo'] == 'investimento']
            if not df_investimentos.empty:
                fig_pie_inv = px.pie(df_investimentos, 
                                 names='categoria', 
                                 values='valor', 
                                 hole=.3)
                fig_pie_inv.update_layout(legend_title_text='Categorias', margin=dict(t=0, b=0, l=0, r=0))
                st.plotly_chart(fig_pie_inv, use_container_width=True)
            else:
                st.info("Nenhum investimento registrado no período.")

# =========================================================================
# === LÓGICA PRINCIPAL: Decide qual página mostrar (Sem mudanças) =========
# =========================================================================
if st.session_state['user'] is None:
    # Se não está logado, mostra a página de login
    show_login_page()
else:
    # Se está logado, mostra o app principal
    show_main_app()