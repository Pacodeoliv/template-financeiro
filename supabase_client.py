# supabase_client.py
import streamlit as st
from supabase import create_client, Client

# Usa st.cache_resource para inicializar a conexão uma única vez.
@st.cache_resource
def init_connection() -> Client:
    """
    Inicializa e retorna o cliente Supabase.
    """
    try:
        url = st.secrets["SUPABASE_URL"]
        key = st.secrets["SUPABASE_KEY"]
        return create_client(url, key)
    except Exception as e:
        st.error(f"Erro ao conectar com o Supabase: {e}")
        return None

supabase_client = init_connection()

# --- Funções de Autenticação (Sem mudanças) ---

def sign_up(email, password):
    try:
        res = supabase_client.auth.sign_up({
            "email": email,
            "password": password,
        })
        return res
    except Exception as e:
        return {"error": str(e)}

def sign_in(email, password):
    try:
        res = supabase_client.auth.sign_in_with_password({
            "email": email,
            "password": password,
        })
        return res
    except Exception as e:
        return {"error": str(e)}

def sign_out():
    try:
        res = supabase_client.auth.sign_out()
        return res
    except Exception as e:
        return {"error": str(e)}

def get_user_session():
    try:
        session = supabase_client.auth.get_session()
        return session
    except Exception as e:
        return None

# --- Funções CRUD (Transactions) ---

def get_transactions(user_id):
    """
    Busca todas as transações de um usuário específico.
    """
    try:
        response = supabase_client.table('transactions') \
                                  .select('*') \
                                  .eq('user_id', user_id) \
                                  .order('data', desc=True) \
                                  .execute()
        return response.data
    except Exception as e:
        st.error(f"Erro ao buscar transações: {e}")
        return []

def add_transaction(user_id, tipo, valor, descricao, categoria, data, card_id=None, installment_group_id=None):
    """
    Adiciona uma ÚNICA nova transação.
    """
    try:
        transaction_data = {
            'user_id': user_id,
            'tipo': tipo,
            'valor': valor,
            'descricao': descricao,
            'categoria': categoria,
            'data': str(data),
            'card_id': card_id,
            'installment_group_id': installment_group_id
        }
        response = supabase_client.table('transactions').insert(transaction_data).execute()
        return response.data
    except Exception as e:
        st.error(f"Erro ao adicionar transação: {e}")
        return None

def add_batch_transactions(transactions_list):
    """
    Adiciona uma lista de transações (parcelas) de uma vez.
    'transactions_list' é uma lista de dicts.
    """
    try:
        response = supabase_client.table('transactions').insert(transactions_list).execute()
        return response.data
    except Exception as e:
        st.error(f"Erro ao adicionar lote de transações: {e}")
        return None

def delete_transaction(transaction_id, user_id):
    """
    Deleta uma transação específica do usuário.
    """
    try:
        response = supabase_client.table('transactions') \
                                  .delete() \
                                  .match({'id': transaction_id, 'user_id': user_id}) \
                                  .execute()
        return response.data
    except Exception as e:
        st.error(f"Erro ao deletar transação: {e}")
        return None


# --- Funções CRUD (Credit Cards) ---

@st.cache_data(ttl=300) # Cache de 5 minutos
def get_credit_cards(user_id):
    """
    Busca todos os cartões de crédito de um usuário.
    """
    try:
        response = supabase_client.table('credit_cards') \
                                  .select('*') \
                                  .eq('user_id', user_id) \
                                  .order('nome_cartao', desc=False) \
                                  .execute()
        return response.data
    except Exception as e:
        st.error(f"Erro ao buscar cartões: {e}")
        return []

# --- MUDANÇA AQUI ---
def add_credit_card(user_id, nome_cartao, limite, dia_vencimento, dia_fechamento):
    """
    Adiciona um novo cartão de crédito.
    """
    try:
        response = supabase_client.table('credit_cards').insert({
            'user_id': user_id,
            'nome_cartao': nome_cartao,
            'limite': limite,
            'dia_vencimento': dia_vencimento,
            'dia_fechamento': dia_fechamento # <--- NOVO CAMPO
        }).execute()
        return response.data
    except Exception as e:
        st.error(f"Erro ao adicionar cartão: {e}")
        return None