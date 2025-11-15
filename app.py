# app.py
import streamlit as st
import supabase_client as sc
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go  # Importação necessária para o gráfico combinado
from datetime import datetime
import time
import uuid # Para agrupar parcelas
from dateutil.relativedelta import relativedelta # Para calcular datas futuras

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

# --- Categorias (Atualizadas com as suas) ---
CATEGORIAS_DESPESA = ['Moradia', 'Alimentação', 'Transporte', 'Lazer', 'Saúde', 'Outros', 'Impostos', 'Cartão de Crédito', 'Empréstimo','Despesas fixas']
CATEGORIAS_RECEITA = ['Salário', 'Freelance', 'Outros', 'Investimentos', 'Vendas']
CATEGORIAS_INVESTIMENTO = ['Ações', 'Fundos Imobiliários', 'Renda Fixa', 'Cripto', 'Outros']


# --- Mapeamento de Meses para Português ---
MESES_PORTUGUES = {
    1: 'Janeiro', 2: 'Fevereiro', 3: 'Março', 4: 'Abril', 
    5: 'Maio', 6: 'Junho', 7: 'Julho', 8: 'Agosto',
    9: 'Setembro', 10: 'Outubro', 11: 'Novembro', 12: 'Dezembro'
}
# ----------------------------------------------------


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

# --- Função Helper para calcular vencimentos ---
def calcular_data_vencimento(data_compra, dia_vencimento, dia_fechamento, parcela_index):
    """
    Calcula a data de vencimento da fatura para uma parcela,
    baseado no dia de fechamento real.
    """
    data_vencimento_base = data_compra.replace(day=dia_vencimento)
    
    # Se o dia de vencimento for MENOR que o dia de fechamento (ex: Vence 10, Fecha 28)
    # A fatura que fecha este mês (Nov) vence no próximo mês (Dez).
    if dia_vencimento < dia_fechamento:
        data_vencimento_base += relativedelta(months=1)
    
    # Se a compra foi ANTES ou NO DIA do fechamento
    if data_compra.day <= dia_fechamento:
        primeira_fatura = data_vencimento_base
    else:
        # A compra foi DEPOIS do fechamento, joga para a próxima fatura
        primeira_fatura = data_vencimento_base + relativedelta(months=1)
        
    # Adiciona os meses das parcelas
    fatura_final = primeira_fatura + relativedelta(months=parcela_index - 1)
    return fatura_final


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
    
    # --- NOVO: Carregar Cartões ---
    cards_list = sc.get_credit_cards(user_id)
    # Cria um dict para facilitar a busca: {'Nome do Cartão': {'id': 1, 'dia_vencimento': 10, 'dia_fechamento': 1}}
    cards_dict = {card['nome_cartao']: card for card in cards_list}


    # --- 1. HEADER E FILTROS ---
    with st.container(): # Container estilizado pelo CSS
        st.title("💰 Meu Planner Financeiro")
        
        if df.empty:
            st.info("Nenhuma transação encontrada. Adicione sua primeira transação abaixo!")
            ano_atual = datetime.now().year
            mes_atual = datetime.now().month
            df_filtered = df # Cria um dataframe vazio para não quebrar os KPIs mensais
            # --- CORREÇÃO PARA TRUNCATE ---
            ano_selecionado = ano_atual
            mes_selecionado = mes_atual
        else:
            # Filtros de Mês e Ano (como no seu HTML)
            df['ano'] = df['data'].dt.year
            df['mes'] = df['data'].dt.month
            
            # --- MUDANÇA: Ordena por DATA (não por ano/mes) ---
            df = df.sort_values(by='data')
            
            anos_disponiveis = sorted(df['ano'].unique(), reverse=True)
            meses_disponiveis = sorted(df['mes'].unique())
            
            ano_atual = datetime.now().year if datetime.now().year in anos_disponiveis else anos_disponiveis[0]
            mes_atual = datetime.now().month if datetime.now().month in meses_disponiveis else meses_disponiveis[0]

            col_filtro1, col_filtro2 = st.columns(2)
            ano_selecionado = col_filtro1.selectbox("Ano", anos_disponiveis, index=anos_disponiveis.index(ano_atual))
            
            # --- MUDANÇA (Tradução) ---
            mes_selecionado = col_filtro2.selectbox("Mês", meses_disponiveis, index=meses_disponiveis.index(mes_atual), 
                                                     format_func=lambda x: MESES_PORTUGUES.get(x, x))

            # Filtrar DataFrame para os KPIs MENSAIS e gráficos
            df_filtered = df[(df['ano'] == ano_selecionado) & (df['mes'] == mes_selecionado)]

    # --- 2. KPIs TOTAIS (Sem filtro de mês) ---
    st.subheader("Visão Geral (Total)")
    receitas_total = df[df['tipo'] == 'receita']['valor'].sum()
    despesas_total = df[df['tipo'] == 'despesa']['valor'].sum()
    investimentos_total = df[df['tipo'] == 'investimento']['valor'].sum()
    saldo_total = receitas_total - despesas_total

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Receita Total", f"R$ {receitas_total:,.2f}")
    col2.metric("Despesa Total", f"R$ {despesas_total:,.2f}")
    col3.metric("Saldo Total", f"R$ {saldo_total:,.2f}")
    col4.metric("Investimentos (Reserva)", f"R$ {investimentos_total:,.2f}")

    # --- 3. KPIs MENSAIS (Com filtro de mês) ---
    # --- MUDANÇA (Tradução) ---
    st.subheader(f"Resumo de {MESES_PORTUGUES.get(mes_selecionado, mes_selecionado)}/{ano_selecionado}")
    receitas_mes = df_filtered[df_filtered['tipo'] == 'receita']['valor'].sum()
    despesas_mes = df_filtered[df_filtered['tipo'] == 'despesa']['valor'].sum()
    investimentos_mes = df_filtered[df_filtered['tipo'] == 'investimento']['valor'].sum()
    saldo_mes = receitas_mes - despesas_mes

    col5, col6, col7, col8 = st.columns(4)
    col5.metric("Receita do Mês", f"R$ {receitas_mes:,.2f}")
    col6.metric("Despesa do Mês", f"R$ {despesas_mes:,.2f}")
    col7.metric("Saldo do Mês", f"R$ {saldo_mes:,.2f}")
    col8.metric("Investimento do Mês", f"R$ {investimentos_mes:,.2f}")
    
    st.markdown("---") # Separador visual

    # --- 4. LAYOUT PRINCIPAL (Gráficos) ---
    col_charts_left, col_charts_right = st.columns([2, 1], gap="large") # 2fr 1fr

    with col_charts_left:
        # --- MUDANÇA: GRÁFICO DE TENDÊNCIA (Visão Mensal com 3 Barras) ---
        with st.container(border=True):
            st.subheader(f"📈 Tendência Acumulada (Toda a História)")
            
            if df.empty:
                st.info(f"Sem dados de transação para mostrar a tendência.")
            else:
                # 1. Agrupa por ANO e MÊS (Voltamos a agrupar)
                df_timeline = df.pivot_table(
                    index=['ano', 'mes'],
                    columns='tipo',
                    values='valor',
                    aggfunc='sum'
                ).fillna(0)
                
                # Garante que todas as colunas de tipo existem
                for col in ['receita', 'despesa', 'investimento']:
                    if col not in df_timeline:
                        df_timeline[col] = 0
                        
                # 2. Calcula o saldo MENSAL (Fluxo de Caixa)
                df_timeline['saldo_mensal'] = df_timeline['receita'] - df_timeline['despesa']
                
                # 3. Calcula o Saldo ACUMULADO VITALÍCIO
                df_timeline['saldo_acumulado_total'] = df_timeline['saldo_mensal'].cumsum()
                
                # 4. Cria os labels do eixo X (ex: "Nov/25", "Dez/25", "Jan/26")
                labels_x = []
                for ano, mes in df_timeline.index:
                    nome_mes_abrev = MESES_PORTUGUES.get(int(mes), str(mes))[:3] # Pega os 3 primeiros caracteres
                    ano_abrev = str(ano)[2:] # Pega os 2 últimos dígitos
                    labels_x.append(f"{nome_mes_abrev}/{ano_abrev}")
                
                # --- 5. Cria o Gráfico Combinado ---
                fig_timeline = go.Figure()

                # --- 3 BARRAS + 1 LINHA ---
                # Barra de Receita
                fig_timeline.add_trace(go.Bar(
                    x=labels_x,
                    y=df_timeline['receita'],
                    name='Receita (Mês)',
                    marker_color='#10b981'
                ))
                
                # Barra de Despesa
                fig_timeline.add_trace(go.Bar(
                    x=labels_x,
                    y=df_timeline['despesa'],
                    name='Despesa (Mês)',
                    marker_color='#ef4444'
                ))
                
                # Barra de Investimento
                fig_timeline.add_trace(go.Bar(
                    x=labels_x,
                    y=df_timeline['investimento'],
                    name='Investimento (Mês)',
                    marker_color='#FFC300' # Amarelo/Ouro
                ))
                
                # Linha de Saldo ACUMULADO TOTAL
                fig_timeline.add_trace(go.Scatter(
                    x=labels_x,
                    y=df_timeline['saldo_acumulado_total'], 
                    name='Saldo Acumulado (Vitalício)',
                    mode='lines+markers',
                    line=dict(color='#667eea', width=3)
                ))

                # Configura o layout
                fig_timeline.update_layout(
                    barmode='group',  # <-- MUDANÇA: Agrupa as barras
                    title=f"Fluxo de Caixa vs. Saldo Acumulado (Toda a História)",
                    xaxis_title="Mês/Ano",
                    yaxis_title="Valor (R$)",
                    legend_title="Métricas",
                    plot_bgcolor='#0E1117', # Fundo do gráfico
                    paper_bgcolor='rgba(0,0,0,0)', # Fundo do papel (transparente)
                    font_color='#FAFAFA' # Cor da fonte para tema escuro
                )
                
                st.plotly_chart(fig_timeline, use_container_width=True)

    with col_charts_right:
        # --- Gráfico de Despesas (Filtrado por Mês) ---
        with st.container(border=True):
            # --- MUDANÇA (Tradução) ---
            st.subheader(f"🏷️ Despesas de {MESES_PORTUGUES.get(mes_selecionado, mes_selecionado)}")
            df_despesas = df_filtered[df_filtered['tipo'] == 'despesa'] if not df_filtered.empty else pd.DataFrame()
            if not df_despesas.empty:
                fig_pie = px.pie(df_despesas, 
                                 names='categoria', 
                                 values='valor', 
                                 hole=.3) # Gráfico de rosca
                
                # --- Adicionado height=150 (como no seu código) ---
                fig_pie.update_layout(
                    height=150, # Define a altura fixa
                    legend_title_text='Categorias', 
                    margin=dict(t=0, b=0, l=0, r=0),
                    plot_bgcolor='rgba(0,0,0,0)',
                    paper_bgcolor='rgba(0,0,0,0)',
                    font_color='#FAFAFA'
                )
                st.plotly_chart(fig_pie, use_container_width=True)
            else:
                st.info("Nenhuma despesa registrada no período.")
        
        # --- Gráfico de Investimentos (Geral / Total) ---
        with st.container(border=True):
            st.subheader(f"📈 Investimentos (Geral)")
            df_investimentos = df[df['tipo'] == 'investimento'] if not df.empty else pd.DataFrame()
            if not df_investimentos.empty:
                fig_pie_inv = px.pie(df_investimentos, 
                                 names='categoria', 
                                 values='valor', 
                                 hole=.3)
                
                # --- Adicionado height=150 (como no seu código) ---
                fig_pie_inv.update_layout(
                    height=150, # Define a altura fixa
                    legend_title_text='Categorias', 
                    margin=dict(t=0, b=0, l=0, r=0),
                    plot_bgcolor='rgba(0,0,0,0)',
                    paper_bgcolor='rgba(0,0,0,0)',
                    font_color='#FAFAFA'
                )
                st.plotly_chart(fig_pie_inv, use_container_width=True)
            else:
                st.info("Nenhum investimento registrado (Geral).")

                
    st.markdown("---") # Separador visual

    # --- 5. CONTEÚDO SECUNDÁRIO (Formulário e Histórico) ---
    
    # --- Formulário de Adição (COM LÓGICA DE CARTÃO) ---
    with st.expander("📝 Adicionar Nova Transação", expanded=df.empty):
        
        tipo = st.selectbox("Tipo", ["despesa", "receita", "investimento"], key="add_tipo_selector")
        
        # --- MUDANÇA: Lógica de Pagamento com Empréstimo ---
        meio_pagamento = "avista" # Padrão
        if tipo == 'despesa':
            meio_pagamento = st.radio("Meio de Pagamento", ["À Vista (Dinheiro/Débito)", "Cartão de Crédito", "Empréstimo"], key="payment_method", horizontal=True)

        with st.form("add_form", clear_on_submit=True):
            
            # --- CORREÇÃO DO BUG: Variável única para Categoria ---
            categoria_final = None
            # ----------------------------------------------------
            
            col_form1, col_form2 = st.columns(2)
            
            with col_form1:
                # --- MUDANÇA: Label do valor muda ---
                valor_label = "Valor (R$)"
                if tipo == 'despesa' and meio_pagamento == "Cartão de Crédito":
                    valor_label = "Valor da Parcela (R$)"
                elif tipo == 'despesa' and meio_pagamento == "Empréstimo":
                    valor_label = "Valor da Parcela (R$)"
                
                valor = st.number_input(valor_label, min_value=0.01, format="%.2f", key="add_valor")
                
                # --- MUDANÇA: Lógica de Categoria e Parcelas ---
                cartao_selecionado_nome = None
                num_parcelas = 1
                
                # --- MUDANÇA: Categoria é selecionada ANTES do meio de pagamento ---
                if tipo == 'despesa':
                    categoria_final = st.selectbox("Categoria", CATEGORIAS_DESPESA, key="add_cat_des")
                elif tipo == 'receita':
                    categoria_final = st.selectbox("Categoria", CATEGORIAS_RECEITA, key="add_cat_rec")
                elif tipo == 'investimento':
                    categoria_final = st.selectbox("Categoria", CATEGORIAS_INVESTIMENTO, key="add_cat_inv")

                # --- MUDANÇA: Lógica de Pagamento SÓ adiciona campos extras ---
                if tipo == 'despesa':
                    if meio_pagamento == "Cartão de Crédito":
                        if not cards_dict:
                            st.error("Nenhum cartão de crédito cadastrado. Adicione um cartão abaixo.")
                        else:
                            cartao_selecionado_nome = st.selectbox("Cartão", list(cards_dict.keys()))
                            num_parcelas = st.number_input("Nº de Parcelas", min_value=1, max_value=48, value=1, step=1)
                    
                    elif meio_pagamento == "Empréstimo":
                        num_parcelas = st.number_input("Nº de Parcelas", min_value=1, max_value=120, value=1, step=1)

            
            with col_form2:
                # --- MUDANÇA: Label da data muda ---
                data_label = "Data da Transação"
                if tipo == 'despesa' and meio_pagamento == "Cartão de Crédito":
                    data_label = "Data da Compra"
                elif tipo == 'despesa' and meio_pagamento == "Empréstimo":
                    data_label = "Data da Primeira Parcela"
                
                data = st.date_input(data_label, datetime.today(), key="add_data")
                descricao = st.text_input("Descrição", placeholder="Ex: Salário, Aluguel, Ações...", key="add_desc")
            
            submitted_add = st.form_submit_button("Adicionar Transação")

            if submitted_add:
                # Lógica de submissão
                try:
                    # --- MUDANÇA: LÓGICA DE SUBMISSÃO ISOLADA ---
                    
                    response = None # Inicializa a resposta
                    
                    if tipo == 'despesa' and meio_pagamento == "Empréstimo":
                        valor_parcela = valor
                        grupo_id = str(uuid.uuid4())
                        batch_list = []
                        for i in range(num_parcelas): # Loop de 0 a N-1
                            data_vencimento = data + relativedelta(months=i)
                            transacao_parcela = {
                                'user_id': user_id,
                                'tipo': 'despesa',
                                'valor': valor_parcela,
                                'descricao': f"{descricao} ({i+1}/{num_parcelas})",
                                'categoria': categoria_final, # <-- CORREÇÃO
                                'data': str(data_vencimento),
                                'installment_group_id': grupo_id
                            }
                            batch_list.append(transacao_parcela)
                        response = sc.add_batch_transactions(batch_list)

                    elif tipo == 'despesa' and meio_pagamento == "Cartão de Crédito":
                        if not cartao_selecionado_nome:
                            st.error("Erro: Nenhum cartão selecionado.")
                            # response continua None
                        else:
                            cartao_info = cards_dict[cartao_selecionado_nome]
                            valor_parcela = valor # Valor do form É o valor da parcela
                            grupo_id = str(uuid.uuid4())
                            batch_list = []
                            for i in range(1, num_parcelas + 1):
                                data_vencimento = calcular_data_vencimento(data, cartao_info['dia_vencimento'], cartao_info['dia_fechamento'], i)
                                transacao_parcela = {
                                    'user_id': user_id,
                                    'tipo': 'despesa',
                                    'valor': valor_parcela,
                                    'descricao': f"{descricao} ({i}/{num_parcelas})",
                                    'categoria': categoria_final, # <-- CORREÇÃO
                                    'data': str(data_vencimento),
                                    'card_id': cartao_info['id'],
                                    'installment_group_id': grupo_id
                                }
                                batch_list.append(transacao_parcela)
                            response = sc.add_batch_transactions(batch_list)

                    elif tipo == 'despesa' and meio_pagamento == "À Vista":
                        transacao_data = data # Data padrão
                        card_id = None # Padrão
                        response = sc.add_transaction(user_id, tipo, valor, descricao, categoria_final, transacao_data, card_id)

                    elif tipo == 'receita':
                        transacao_data = data
                        card_id = None
                        response = sc.add_transaction(user_id, tipo, valor, descricao, categoria_final, transacao_data, card_id)

                    elif tipo == 'investimento':
                        transacao_data = data
                        card_id = None
                        response = sc.add_transaction(user_id, tipo, valor, descricao, categoria_final, transacao_data, card_id)

                    # --- VERIFICAÇÃO DE SUCESSO CENTRALIZADA ---
                    if response:
                        st.success("Transação adicionada!")
                        st.cache_data.clear()
                        st.rerun()
                    else:
                        # Se response é None (ex: erro no cartão), não mostra msg duplicada
                        if cartao_selecionado_nome is not None: 
                            st.error("Falha ao adicionar transação.")
                
                except Exception as e:
                    st.error(f"Erro ao processar transação: {e}")

    # --- NOVO: Expander para Gerenciar Cartões ---
    with st.expander("💳 Gerenciar Cartões de Crédito"):
        st.subheader("Adicionar Novo Cartão")
        with st.form("add_card_form", clear_on_submit=True):
            col_card1, col_card2, col_card3 = st.columns(3)
            with col_card1:
                nome_cartao = st.text_input("Nome do Cartão (Ex: Nubank)")
            with col_card2:
                # --- MUDANÇA: Campo de Fechamento ---
                dia_fechamento = st.number_input("Dia do Fechamento", min_value=1, max_value=31, value=28, step=1)
            with col_card3:
                dia_vencimento = st.number_input("Dia do Vencimento", min_value=1, max_value=31, value=10, step=1)
            
            # Limite separado para mais espaço
            limite_cartao = st.number_input("Limite (R$)", min_value=0.0, format="%.2f")
            
            submitted_card = st.form_submit_button("Adicionar Cartão")
            
            if submitted_card:
                if not nome_cartao or dia_vencimento <= 0 or dia_fechamento <= 0:
                    st.warning("Preencha todos os campos do cartão.")
                else:
                    # --- MUDANÇA: Passa o dia_fechamento ---
                    response = sc.add_credit_card(user_id, nome_cartao, limite_cartao, dia_vencimento, dia_fechamento)
                    if response:
                        st.success(f"Cartão '{nome_cartao}' adicionado!")
                        st.cache_data.clear()
                        st.rerun()
                    else:
                        st.error("Falha ao adicionar cartão.")

        st.subheader("Meus Cartões")
        if not cards_list:
            st.info("Nenhum cartão cadastrado.")
        else:
            # --- MUDANÇA: Mostra o dia_fechamento ---
            df_cards = pd.DataFrame(cards_list)[['nome_cartao', 'limite', 'dia_fechamento', 'dia_vencimento']]
            st.dataframe(df_cards, use_container_width=True, hide_index=True)


    # --- Histórico de Transações (agora é um expander) ---
    with st.expander(f"📊 Histórico de Transações de {MESES_PORTUGUES.get(mes_selecionado, mes_selecionado)}"):
        if df_filtered.empty:
            st.info("Nenhuma transação para este mês.")
        else:
            # --- MUDANÇA: Lógica para Deletar Transação ---
            st.subheader("Deletar Transação")
            
            # Criar um dicionário de mapeamento 'Display String' -> 'ID'
            # Usamos o ID da transação no dataframe filtrado
            delete_options_map = {
                # --- MUDANÇA: Adiciona o ID na frente para evitar duplicatas ---
                f"ID {row['id']}: {row['data'].strftime('%d/%m/%Y')} - {row['descricao']} - R$ {row['valor']:.2f}": row['id']
                for index, row in df_filtered.iterrows()
            }
            
            # Adiciona uma opção "Nenhum" no começo
            options_list = ["Selecione uma transação para deletar..."] + list(delete_options_map.keys())
            
            selected_option = st.selectbox("Selecione a Transação", options_list)
            
            if st.button("Deletar Transação Selecionada", type="primary", disabled=(selected_option == options_list[0])):
                try:
                    # Pega o ID da transação a ser deletada
                    transaction_id_to_delete = delete_options_map[selected_option]
                    
                    # Chama a função do client
                    response = sc.delete_transaction(transaction_id_to_delete, user_id)
                    
                    if response:
                        st.success("Transação deletada com sucesso!")
                        st.cache_data.clear() # Limpa o cache
                        st.rerun()
                    else:
                        st.error("Erro ao deletar transação.")
                except Exception as e:
                    st.error(f"Erro: {e}")

            # Exibe o dataframe
            st.subheader("Transações do Mês")
            st.dataframe(
                # --- MUDANÇA: Mostra o ID da transação ---
                df_filtered[['id', 'data', 'descricao', 'categoria', 'tipo', 'valor']],
                use_container_width=True,
                hide_index=True
            )
        

# =========================================================================
# === LÓGICA PRINCIPAL: Decide qual página mostrar (Sem mudanças) =========
# =========================================================================
if st.session_state['user'] is None:
    # Se não está logado, mostra a página de login
    show_login_page()
else:
    # Se está logado, mostra o app principal
    show_main_app()