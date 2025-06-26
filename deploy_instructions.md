# 🚀 Guia de Deploy - Dashboard CNPJ Alfanumérico

## 📋 Opções de Deploy

### 1. 🆓 Streamlit Community Cloud (RECOMENDADO)

**Vantagens:** Gratuito, fácil, automático
**Limitações:** Repositório deve ser público
**Tempo:** 5-10 minutos

#### Passos:
1. **Criar repositório no GitHub:**
   ```bash
   git init
   git add .
   git commit -m "Dashboard CNPJ Alfanumérico"
   git branch -M main
   git remote add origin https://github.com/SEU_USUARIO/refinamento-cnpj
   git push -u origin main
   ```

2. **Deploy no Streamlit Cloud:**
   - Acesse: https://share.streamlit.io/
   - Conecte sua conta GitHub
   - Clique em "New app"
   - Selecione o repositório `refinamento-cnpj`
   - Main file: `dashboard.py`
   - Clique "Deploy!"

3. **Seu dashboard estará disponível em:**
   `https://SEU_USUARIO-refinamento-cnpj-dashboard-xxx.streamlit.app`

---

### 2. 🌐 Railway (ALTERNATIVA MODERNA)

**Vantagens:** Deploy simples, domínio customizado
**Custo:** $5/mês (com domínio próprio)

#### Passos:
1. Acesse: https://railway.app/
2. Conecte GitHub
3. "Deploy from GitHub repo"
4. Selecione o repositório
5. Railway detecta automaticamente o Streamlit

---

### 3. ☁️ Heroku (PROFISSIONAL)

**Vantagens:** Robusto, escalável
**Custo:** ~$7/mês (Eco Dynos)

#### Arquivos necessários:

**Procfile:**
```
web: streamlit run dashboard.py --server.port=$PORT --server.address=0.0.0.0
```

**runtime.txt:**
```
python-3.11
```

#### Deploy:
```bash
heroku create nome-do-app
git push heroku main
```

---

### 4. 🏢 Azure/AWS (EMPRESARIAL)

**Para ambientes corporativos com maior controle e segurança**

#### Azure Container Instances:
- Dockerfile + Azure CLI
- Integração com AD corporativo
- ~$15-30/mês

#### AWS Lightsail:
- Deploy via Docker
- Load balancer automático
- ~$20-40/mês

---

## 🔧 Configurações Importantes

### Variáveis de Ambiente (se necessário):
```bash
STREAMLIT_SERVER_HEADLESS=true
STREAMLIT_SERVER_PORT=8501
STREAMLIT_BROWSER_GATHER_USAGE_STATS=false
```

### Para repositórios privados:
- Use Railway ou Heroku
- Configure secrets/tokens se necessário

### Domínio personalizado:
- Cloudflare (gratuito) + Railway/Heroku
- Exemplo: `dashboard-cnpj.suaempresa.com`

---

## 🚨 Checklist Pré-Deploy

- [ ] Arquivo `requirements.txt` atualizado
- [ ] Configuração `.streamlit/config.toml` criada
- [ ] Dados de exemplo funcionando
- [ ] Teste local `streamlit run dashboard.py`
- [ ] Repositório Git configurado
- [ ] README.md com instruções

---

## 🔐 Considerações de Segurança

### Para dados sensíveis:
1. **Autenticação:** Implementar login simples
2. **IP Whitelist:** Restringir acesso por IP
3. **HTTPS:** Sempre usar conexões seguras
4. **Dados Mock:** Considerar dados anonimizados

### Implementação simples de auth:
```python
import streamlit as st

def check_password():
    def password_entered():
        if st.session_state["password"] == "senha_gps_2024":
            st.session_state["password_correct"] = True
            del st.session_state["password"]
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        st.text_input("Senha", type="password", on_change=password_entered, key="password")
        return False
    elif not st.session_state["password_correct"]:
        st.text_input("Senha", type="password", on_change=password_entered, key="password")
        st.error("Senha incorreta")
        return False
    else:
        return True

# No início do dashboard.py:
if not check_password():
    st.stop()
```

---

## 📞 Suporte

Para problemas com deploy:
1. Verifique logs da plataforma
2. Teste localmente primeiro
3. Consulte documentação específica da plataforma
4. Considere usar dados menores para testes 