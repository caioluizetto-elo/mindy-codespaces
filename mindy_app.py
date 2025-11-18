# -*- coding: utf-8 -*-
# mindy_app.py — Mindy Assistant (Meta-Cortex)
# App Streamlit com sistema de autenticação

from __future__ import annotations

import os
import sys
import hashlib
from pathlib import Path
from typing import Dict, List

import streamlit as st

# ---------------------------------------------------------
# Ajuste de path para importar core/*
# ---------------------------------------------------------
ROOT = Path(__file__).resolve().parents[1]  # .../MINDY_ASSISTANT
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core import auth
from core import kernel as mindy_kernel
from core import memory_store
from core import directives_store
from core.file_manager import file_manager

# Voz é opcional — não quebra se o módulo não existir
try:
    from core import voice as mindy_voice  # type: ignore
except Exception:  # noqa: BLE001
    mindy_voice = None  # type: ignore

# Configura usuário padrão na primeira execução
auth.setup_default_user()

# Caminho raiz fixo
ROOT_PATH = Path(r"C:\Users\Caio\Documents\Synapse\MINDY_ASSISTANT")
USER_FILES_PATH = ROOT_PATH / "user_files"
USER_FILES_PATH.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------
# Estilo / CSS minimalista
# ---------------------------------------------------------
MINDY_CSS = """
<style>
/* Zera um pouco o padding global */
.block-container {
    padding-top: 1.5rem;
    padding-bottom: 1.5rem;
}

/* Cabeçalho centralizado da Mindy */
.mindy-hero {
    text-align: center;
    margin-bottom: 1.5rem;
    padding: 1.25rem 1rem 1.0rem 1rem;
}

.mindy-eyebrow {
    font-size: 0.75rem;
    text-transform: uppercase;
    letter-spacing: 0.22em;
    color: #6b7280;
    margin-bottom: 0.35rem;
}

.mindy-title {
    font-size: 2.2rem;
    font-weight: 700;
    line-height: 1.15;
    margin: 0;
    background: linear-gradient(90deg, #7c3aed, #db2777);
    -webkit-background-clip: text;
    -moz-background-clip: text;
    background-clip: text;
    color: transparent;
}

/* Estilo para a página de login */
.login-container {
    max-width: 400px;
    margin: 0 auto;
    padding: 2rem;
    border: 1px solid #e5e7eb;
    border-radius: 10px;
    background: white;
    box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
}
</style>
"""

def _render_header() -> None:
    st.markdown(MINDY_CSS, unsafe_allow_html=True)
    st.markdown(
        """
        <div class="mindy-hero">
          <div class="mindy-eyebrow">SYNAPSE / META-CORTEX ASSISTANT</div>
          <h1 class="mindy-title">Mindy Assistant</h1>
        </div>
        """,
        unsafe_allow_html=True,
    )

# ---------------------------------------------------------
# Página de Login
# ---------------------------------------------------------
def login_page():
    """Página de autenticação"""
    st.markdown(MINDY_CSS, unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown('<div class="login-container">', unsafe_allow_html=True)
        
        st.markdown("### 🔐 Acesso Mindy")
        st.markdown("Faça login para acessar a assistente cognitiva")
        
        tab1, tab2 = st.tabs(["🚪 Login", "📝 Registrar"])
        
        with tab1:
            username = st.text_input("Usuário", key="login_user")
            password = st.text_input("Senha", type="password", key="login_pass")
            
            if st.button("Entrar", type="primary", use_container_width=True, key="login_btn"):
                if auth.authenticate(username, password):
                    st.session_state.authenticated = True
                    st.session_state.username = username
                    st.success("Login realizado com sucesso!")
                    st.rerun()
                else:
                    st.error("Usuário ou senha incorretos")
            
            st.markdown("---")
            st.caption("💡 **Credenciais padrão:**")
            st.caption("Usuário: `admin` | Senha: `admin123`")
        
        with tab2:
            new_user = st.text_input("Novo usuário", key="reg_user")
            new_pass = st.text_input("Nova senha", type="password", key="reg_pass")
            confirm_pass = st.text_input("Confirmar senha", type="password", key="reg_confirm")
            name = st.text_input("Nome completo", key="reg_name")
            email = st.text_input("Email", key="reg_email")
            
            if st.button("Criar conta", use_container_width=True, key="register_btn"):
                if not all([new_user, new_pass, confirm_pass, name, email]):
                    st.error("Preencha todos os campos")
                elif new_pass != confirm_pass:
                    st.error("Senhas não coincidem")
                elif len(new_pass) < 6:
                    st.error("Senha deve ter pelo menos 6 caracteres")
                else:
                    if auth.register_user(new_user, new_pass, name, email):
                        st.success("Conta criada com sucesso! Faça login.")
                    else:
                        st.error("Usuário já existe")
        
        st.markdown('</div>', unsafe_allow_html=True)

# ---------------------------------------------------------
# Helpers de sessão (após login)
# ---------------------------------------------------------
def _init_session() -> None:
    if "chat_history" not in st.session_state:
        st.session_state["chat_history"]: List[Dict[str, str]] = []
    if "temperature" not in st.session_state:
        st.session_state["temperature"] = 0.4
    if "mindy_memory" not in st.session_state:
        try:
            st.session_state["mindy_memory"] = memory_store.load_memory()
        except Exception:  # noqa: BLE001
            st.session_state["mindy_memory"] = {"items": []}
    if "mindy_voice_on" not in st.session_state:
        st.session_state["mindy_voice_on"] = False
    if "arquivos_ativos" not in st.session_state:
        st.session_state["arquivos_ativos"] = set()

def _add_message(role: str, content: str) -> None:
    st.session_state["chat_history"].append({"role": role, "content": content})

# ---------------------------------------------------------
# Layout principal (após login)
# ---------------------------------------------------------
def main_app():
    """Aplicação principal após login"""
    _init_session()

    # ---------------- Sidebar ----------------
    with st.sidebar:
        # Header com informações do usuário
        st.title(f"🧠 Mindy")
        st.markdown(f"**Usuário:** {st.session_state.username}")
        
        # Botão de logout
        if st.button("🚪 Sair", use_container_width=True, key="sidebar_logout_btn"):
            auth.logout()
        
        st.markdown("---")
        
        st.markdown("**Configuração do modelo**")
        api_key = st.text_input(
            "OPENAI_API_KEY",
            type="password",
            value=os.getenv("OPENAI_API_KEY", ""),
            help="Sua chave da OpenAI. Fica apenas neste ambiente local.",
            key="sidebar_api_key"
        )
        if api_key:
            os.environ["OPENAI_API_KEY"] = api_key

        model_name = st.text_input(
            "Modelo (opcional)",
            value=os.getenv("MANDY_MODEL", "gpt-4.1-mini"),
            help="Nome do modelo usado pela Mindy (ex.: gpt-4.1-mini, gpt-4.1, gpt-5.1-mini...).",
            key="sidebar_model_name"
        )
        os.environ["MANDY_MODEL"] = model_name

        st.markdown("**Temperatura**")
        temp = st.slider(
            "Criatividade",
            0.0,
            1.0,
            float(st.session_state["temperature"]),
            0.05,
            key="sidebar_temperature"
        )
        st.session_state["temperature"] = temp

        st.markdown("---")
        # Voz opcional
        st.markdown("**Voz da Mindy (opcional)**")
        voice_on = st.toggle(
            "🔊 Ativar voz (TTS)",
            value=bool(st.session_state.get("mindy_voice_on", False)),
            help="Requer OPENAI_API_KEY e suporte ao modelo de voz.",
            key="sidebar_voice_toggle"
        )
        st.session_state["mindy_voice_on"] = voice_on

        if voice_on:
            if mindy_voice is None or not getattr(mindy_voice, "tts_enabled", lambda: False)():
                st.caption("⚠️ TTS ainda não disponível (verifique core/voice.py e OPENAI_API_KEY).")
            else:
                st.caption("✅ Voz pronta para falar.")

        st.markdown("---")
        if st.button("🧹 Limpar conversa", use_container_width=True, key="sidebar_clear_chat_btn"):
            st.session_state["chat_history"] = []
            st.success("Histórico de conversa limpo.")
            st.rerun()

        st.markdown("---")
        # Resumo rápido de memórias/diretrizes
        try:
            mem_data = st.session_state.get("mindy_memory", memory_store.load_memory())
            mem_items = mem_data.get("items", [])
        except Exception:  # noqa: BLE001
            mem_items = []

        try:
            directives = directives_store.list_directives(limit=50)
        except Exception:  # noqa: BLE001
            directives = []

        st.caption(
            f"Memória geral: **{len(mem_items)}** notas · "
            f"Diretrizes cognitivas: **{len(directives)}**"
        )

    # ---------------- Header ----------------
    _render_header()

    # ---------------- Tabs: Chat / Memória / Arquivos ----------------
    tab_chat, tab_memory, tab_files = st.tabs(["💬 Chat", "🧠 Memória", "📁 Arquivos"])

    # =====================================================
    # 💬 Aba 1 — Chat (CORRIGIDA)
    # =====================================================
    with tab_chat:
        st.markdown("### 📋 Arquivos Disponíveis para o Chat")
        st.markdown("Selecione os arquivos que deseja usar na conversa (gerenciados na aba 📁 Arquivos):")
        
        # Lista TODOS os arquivos disponíveis
        all_files = file_manager.list_user_files()
        
        if all_files:
            ativos = st.session_state.get("arquivos_ativos", set())
            novos_ativos = set()
            
            for i, file_info in enumerate(all_files):
                with st.container():
                    col1, col2, col3 = st.columns([3, 1, 1])
                    with col1:
                        # ✅ KEY ÚNICA: usa hash para evitar duplicatas
                        filename_hash = hashlib.md5(file_info['filename'].encode()).hexdigest()[:8]
                        unique_key = f"chat_file_{i}_{filename_hash}"
                        
                        checked = st.checkbox(
                            f"**{file_info['filename']}** ({file_info['size']:,} bytes)", 
                            value=file_info['filename'] in ativos, 
                            key=unique_key
                        )
                    with col2:
                        st.caption(f"📂 {file_info['folder']}")
                    with col3:
                        if file_info.get('tags'):
                            st.caption("🏷️ " + ", ".join(file_info['tags'][:2]))
                    
                    if checked:
                        novos_ativos.add(file_info['filename'])
                    
                    st.markdown("---")
            
            st.session_state["arquivos_ativos"] = novos_ativos
            
            if novos_ativos:
                st.success(f"📎 {len(novos_ativos)} arquivo(s) selecionado(s) para o chat")
                
                with st.expander("💡 Exemplos de como perguntar sobre arquivos"):
                    st.markdown("""
                    **Padrões de perguntas que a Mindy entende:**
                    
                    - "**No arquivo [nome]**, quais são as principais conclusões?"
                    - "**Analise o documento** [nome] e me explique os dados"
                    - "**Baseado no arquivo** [nome], quais são os prazos?"
                    - "**No texto** [nome], qual é a opinião do autor?"
                    - "**Segundo o documento** [nome], quais são os requisitos?"
                    - "**Leia o arquivo** [nome] e me explique a função principal"
                    
                    **💡 Dica:** Para gerenciar arquivos (upload, pastas, tags), use a aba **📁 Arquivos**
                    """)
            else:
                st.info("👆 Selecione algum arquivo acima para conversar sobre ele")
        else:
            st.info("📁 Nenhum arquivo disponível. Vá para a aba **📁 Arquivos** para fazer upload.")
        
        st.markdown("---")
        
        # Histórico do chat
        for msg in st.session_state["chat_history"]:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])

        # Entrada do usuário
        user_text = st.chat_input("Fale com a Mindy...")
        if user_text:
            # registra mensagem do usuário
            _add_message("user", user_text)

            with st.chat_message("user"):
                st.markdown(user_text)

            # processa com kernel da Mindy
            resposta = mindy_kernel.processar_mensagem(
                user_text=user_text,
                chat_history=st.session_state["chat_history"],
                temperature=st.session_state["temperature"],
                arquivos_ativos=list(st.session_state.get("arquivos_ativos", [])),
            )

            reply_text = resposta.get("reply", "")
            intent = resposta.get("intent", {})

            # mostra resposta
            with st.chat_message("assistant"):
                st.markdown(reply_text)

                # Debug opcional (intenção/meta)
                with st.expander("Ver intenção detectada / meta (debug)", expanded=False):
                    st.json(intent)
                    st.json(resposta.get("meta", {}))

                # 🔊 Voz opcional com AUTOPLAY
            voice_on = st.session_state.get("mindy_voice_on", False)
            if voice_on and mindy_voice is not None:
                try:
                    if mindy_voice.tts_enabled():
                        audio_path = mindy_voice.synthesize_to_wav(
                            reply_text,
                            filename_hint="mindy_reply",
                        )
                        if audio_path and audio_path.exists():
                            audio_bytes = audio_path.read_bytes()
                            
                            # Método 1: Tentar autoplay via HTML (funciona na maioria dos casos)
                            import base64
                            
                            # Converte bytes para base64
                            audio_base64 = base64.b64encode(audio_bytes).decode()
                            
                            # Cria elemento de áudio com autoplay
                            audio_html = f"""
                                <audio autoplay controls style="width: 100%">
                                    <source src="data:audio/mp3;base64,{audio_base64}" type="audio/mp3">
                                    Seu navegador não suporta o elemento de áudio.
                                </audio>
                            """
                            st.markdown(audio_html, unsafe_allow_html=True)
                            
                            # Método 2: Fallback - mostra o player normal (sem autoplay)
                            # st.audio(audio_bytes, format="audio/mp3")
                            
                        else:
                            st.caption("⚠️ Não consegui gerar o áudio desta resposta.")
                    else:
                        st.caption("⚠️ TTS não está habilitado no momento.")
                except Exception as e:
                    st.caption(f"⚠️ Erro ao gerar áudio: {e}")

    # =====================================================
    # 🧠 Aba 2 — Memória (notas + diretrizes)
    # =====================================================
    with tab_memory:
        st.subheader("Memória da Mindy & Diretrizes Cognitivas")

        # --- Memória geral (mandy_memory.json) ---
        try:
            mem_data = st.session_state.get("mindy_memory", memory_store.load_memory())
            items = mem_data.get("items", [])
        except Exception:  # noqa: BLE001
            mem_data = {"items": []}
            items = []

        st.markdown(
            f"- Notas atualmente salvas: **{len(items)}**  \n"
            f"- Arquivo: `mandy_memory.json` na pasta do core"
        )

        col_left, col_right = st.columns([2, 1])

        # ------------ Adicionar nova nota ------------  
        with col_left:
            st.markdown("### Adicionar nota manual")

            new_text = st.text_area(
                "Texto da nota",
                placeholder="Ex.: Mindy entende que o domínio IA é prioritário para experimentos de ESG...",
                key="memory_new_note",
                height=120,
            )
            tags_raw = st.text_input(
                "Tags (opcional, separadas por vírgula)",
                key="memory_new_tags",
                placeholder="prioridade, IA, ESG",
            )

            if st.button("➕ Adicionar à memória", key="memory_add_button"):
                if new_text.strip():
                    tags = [
                        t.strip()
                        for t in tags_raw.split(",")
                        if t.strip()
                    ] if tags_raw else []
                    mem_data = memory_store.add_memory(
                        new_text.strip(),
                        kind="manual",
                        tags=tags,
                        source="user",
                    )
                    st.session_state["mindy_memory"] = mem_data
                    st.success("Nota adicionada à memória da Mindy.")
                    st.rerun()
                else:
                    st.warning("Digite algum texto para adicionar à memória.")

        # ------------ Controles da memória ------------  
        with col_right:
            st.markdown("### Controles")

            if st.button("🔄 Recarregar memória do disco", key="memory_reload_button"):
                st.session_state["mindy_memory"] = memory_store.load_memory()
                st.success("Memória recarregada do arquivo.")
                st.rerun()

            if st.button("💾 Salvar memória atual em disco", key="memory_save_button"):
                memory_store.save_memory(st.session_state.get("mindy_memory", {"items": []}))
                st.success("Memória salva em mandy_memory.json.")

            st.markdown("---")
            if st.button("⚠️ Limpar TODA a memória", key="memory_clear_button"):
                mem_data = memory_store.clear_memory()
                st.session_state["mindy_memory"] = mem_data
                st.warning("Toda a memória da Mindy foi limpa.")
                st.rerun()

        st.markdown("---")
        st.markdown("### Notas em memória")

        if not items:
            st.info("Ainda não há notas salvas.")
        else:
            import pandas as pd

            df = pd.DataFrame(items)
            if "ts" in df.columns:
                df = df.sort_values("ts", ascending=False)

            cols_order = [
                c
                for c in ["id", "ts", "kind", "source", "tags", "text"]
                if c in df.columns
            ]
            df = df[cols_order]

            st.dataframe(df, use_container_width=True, hide_index=True)

        # --- Diretrizes Cognitivas (mindy_directives.json) ---
        st.markdown("---")
        st.markdown("### Diretrizes Cognitivas (focos de longo prazo)")

        try:
            directives = directives_store.list_directives(limit=50)
        except Exception:  # noqa: BLE001
            directives = []

        if not directives:
            st.info("Ainda não há Diretrizes Cognitivas registradas.")
        else:
            import pandas as pd

            df_dirs = pd.DataFrame(directives)
            if "created_at" in df_dirs.columns:
                df_dirs = df_dirs.sort_values("created_at", ascending=False)
            st.dataframe(df_dirs, use_container_width=True, hide_index=True)

            # Campo simples para arquivar alguma diretriz
            st.markdown("#### Arquivar uma diretriz pelo ID")
            dir_id_str = st.text_input(
                "ID da diretriz para arquivar",
                key="directive_archive_id",
                placeholder="Ex.: 1",
            )
            if st.button("Arquivar diretriz", key="directive_archive_button"):
                try:
                    dir_id = int(dir_id_str)
                    ok, removed = directives_store.archive_directive(dir_id)
                    if ok:
                        st.success(
                            f"Diretriz Cognitiva (id={dir_id}) arquivada.\n"
                            f"Foco em: {', '.join(removed.get('domains') or []) or removed.get('text', '')}"
                        )
                        st.rerun()
                    else:
                        st.warning(f"Não encontrei diretriz com id={dir_id}.")
                except ValueError:
                    st.error("Informe um ID numérico válido.")
                except Exception as e:  # noqa: BLE001
                    st.error(f"Erro ao arquivar diretriz: {e}")

    # =====================================================
    # 📁 Aba 3 — Gerenciador de Arquivos
    # =====================================================
    with tab_files:
        st.subheader("📁 Gerenciador de Arquivos")
        st.markdown("Faça upload e organize seus arquivos em pastas para usar no chat com a Mindy.")
        
        # --- Upload de arquivos ---
        st.markdown("### 📤 Upload de Arquivos")
        
        uploaded_files_manager = st.file_uploader(
            "Envie seus arquivos aqui",
            type=["txt", "pdf", "md", "json", "py", "csv", "doc", "docx"],
            key="file_uploader_manager",
            help="Os arquivos serão salvos e você poderá organizá-los em pastas",
            accept_multiple_files=True
        )
        
        if uploaded_files_manager:
            for uploaded_file in uploaded_files_manager:
                save_path = USER_FILES_PATH / uploaded_file.name
                with open(save_path, "wb") as f:
                    f.write(uploaded_file.getbuffer())
                
                # Se estiver em uma pasta específica, move para lá
                if selected_folder != "Geral":
                    file_manager.move_file_to_folder(uploaded_file.name, selected_folder)
                
                st.success(f"✅ '{uploaded_file.name}' salvo em '{selected_folder}'!")
                st.rerun()

        st.markdown("---")
        
        # --- Controles principais ---
        col1, col2, col3 = st.columns([2, 1, 1])
        
        with col1:
            # Seletor de pasta
            folders = file_manager.get_folders()
            selected_folder = st.selectbox(
                "📂 Pasta atual:",
                options=folders,
                key="file_manager_folder"
            )
        
        with col2:
            # Criar nova pasta
            with st.popover("➕ Nova pasta", use_container_width=True):
                new_folder = st.text_input("Nome da pasta:", key="new_folder_input")
                if st.button("Criar", key="create_folder_btn"):
                    if new_folder.strip():
                        if file_manager.create_folder(new_folder.strip()):
                            st.success(f"Pasta '{new_folder}' criada!")
                            st.rerun()
                        else:
                            st.error("Pasta já existe!")
        
        with col3:
            # Deletar pasta atual (se não for Geral)
            if selected_folder != "Geral":
                if st.button("🗑️ Deletar pasta", use_container_width=True, key="delete_folder_btn"):
                    if file_manager.delete_folder(selected_folder):
                        st.success(f"Pasta '{selected_folder}' deletada!")
                        st.rerun()
                    else:
                        st.error("Não foi possível deletar a pasta")
        
        st.markdown("---")
        
        # --- Lista de arquivos na pasta selecionada ---
        files = file_manager.list_user_files(selected_folder)
        
        if not files:
            st.info(f"📭 Nenhum arquivo na pasta '{selected_folder}'.")
        else:
            st.markdown(f"**📋 Arquivos em '{selected_folder}':**")
            
            for file_info in files:
                with st.container():
                    col1, col2, col3, col4 = st.columns([3, 2, 1, 1])
                    
                    with col1:
                        st.markdown(f"**{file_info['filename']}**")
                        st.caption(f"Tamanho: {file_info['size']:,} bytes")
                    
                    with col2:
                        # Tags do arquivo
                        tags = file_info.get('tags', [])
                        if tags:
                            st.markdown("🏷️ " + ", ".join(tags))
                        else:
                            st.caption("Sem tags")
                    
                    with col3:
                        # Mover para pasta
                        with st.popover("📂 Mover", use_container_width=True):
                            target_folder = st.selectbox(
                                "Mover para:",
                                options=[f for f in folders if f != selected_folder],
                                key=f"move_select_{file_info['filename']}"
                            )
                            if st.button("Mover", key=f"move_btn_{file_info['filename']}"):
                                if file_manager.move_file_to_folder(file_info['filename'], target_folder):
                                    st.success("Arquivo movido!")
                                    st.rerun()
                    
                    with col4:
                        # Gerenciar tags
                        with st.popover("🏷️ Tags", use_container_width=True):
                            current_tags = file_info.get('tags', [])
                            new_tags = st.text_input(
                                "Tags (separadas por vírgula):",
                                value=", ".join(current_tags),
                                key=f"tags_input_{file_info['filename']}"
                            )
                            col_btn1, col_btn2 = st.columns(2)
                            with col_btn1:
                                if st.button("💾 Salvar", key=f"save_tags_{file_info['filename']}"):
                                    tags_list = [t.strip() for t in new_tags.split(",") if t.strip()]
                                    if file_manager.add_file_tags(file_info['filename'], tags_list):
                                        st.success("Tags atualizadas!")
                                        st.rerun()
                            with col_btn2:
                                if st.button("🗑️ Deletar", key=f"delete_file_{file_info['filename']}"):
                                    if file_manager.delete_file(file_info['filename']):
                                        st.success("Arquivo deletado!")
                                        st.rerun()
                    
                    # Preview do arquivo
                    with st.expander("👁️ Preview", expanded=False):
                        try:
                            content = file_manager.get_file_content(file_info['filename'], max_chars=1000)
                            if content:
                                st.text_area(
                                    f"Conteúdo de {file_info['filename']}:",
                                    content,
                                    height=150,
                                    key=f"preview_{file_info['filename']}"
                                )
                            else:
                                st.error("Não foi possível ler o arquivo")
                        except Exception as e:
                            st.error(f"Erro ao ler arquivo: {e}")
                    
                    st.markdown("---")
        
        # --- Estatísticas ---
        st.markdown("### 📊 Estatísticas")
        col_stat1, col_stat2, col_stat3 = st.columns(3)
        
        total_files = len(file_manager.list_user_files())
        total_size = sum(f["size"] for f in file_manager.list_user_files())
        
        with col_stat1:
            st.metric("Total de Arquivos", total_files)
        
        with col_stat2:
            st.metric("Espaço Usado", f"{total_size / 1024 / 1024:.1f} MB")
        
        with col_stat3:
            st.metric("Pastas", len(folders))

# ---------------------------------------------------------
# App Principal
# ---------------------------------------------------------
def main() -> None:
    st.set_page_config(
        page_title="Mindy Assistant — Synapse",
        page_icon="🧠",
        layout="wide",
    )
    
    # Inicializa estado de autenticação
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False
    if "username" not in st.session_state:
        st.session_state.username = None
    
    # Mostra login ou app principal
    if not auth.is_logged_in():
        login_page()
    else:
        main_app()

if __name__ == "__main__":
    main()