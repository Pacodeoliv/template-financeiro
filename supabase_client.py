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

# --- Funções de Autenticação ---

def sign_up(email, password):
    """
    Registra um novo usuário.
    """
    try:
        res = supabase_client.auth.sign_up({
            "email": email,
            "password": password,
        })
        return res
    except Exception as e:
        return {"error": str(e)}

def sign_in(email, password):
    """
    Autentica um usuário existente.
    """
    try:
        res = supabase_client.auth.sign_in_with_password({
            "email": email,
            "password": password,
        })
        return res
    except Exception as e:
        return {"error": str(e)}

def sign_out():
    """
    Desloga o usuário.
    """
    try:
        res = supabase_client.auth.sign_out()
        return res
    except Exception as e:
        return {"error": str(e)}

def get_user_session():
    """
    Verifica se existe uma sessão de usuário ativa.
    """
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

def add_transaction(user_id, tipo, valor, descricao, categoria, data):
    """
    Adiciona uma nova transação.
    """
    try:
        response = supabase_client.table('transactions').insert({
            'user_id': user_id,
            'tipo': tipo,
            'valor': valor,
            'descricao': descricao,
            'categoria': categoria,
            'data': str(data) # Converte data para string no formato YYYY-MM-DD
        }).execute()
        return response.data
    except Exception as e:
        st.error(f"Erro ao adicionar transação: {e}")
        return None

def update_transaction(transaction_id, user_id, updates):
    """
    Atualiza uma transação existente.
    'updates' é um dicionário com os campos a atualizar.
    """
    try:
        response = supabase_client.table('transactions') \
                                  .update(updates) \
                                  .match({'id': transaction_id, 'user_id': user_id}) \
                                  .execute()
        return response.data
    except Exception as e:
        st.error(f"Erro ao atualizar transação: {e}")
        return None

def delete_transaction(transaction_id, user_id):
    """
    Deleta uma transação.
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