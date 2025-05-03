Documentação Completa: FURIA Esports Bot
(Atualizado em: 05/03/2025)

🚀 Visão Geral do Projeto
FURIA Esports Bot é um chatbot interativo desenvolvido para fornecer informações em tempo real sobre os times de eSports da FURIA (CS2, Valorant e League of Legends). O bot utiliza web scraping da Liquipedia para coletar dados de jogadores e partidas, oferecendo uma interface de chat intuitiva com suporte a temas claro/escuro e recursos de edição de mensagens.

Tecnologias Principais:

Backend: Python + Flask + Socket.IO

Frontend: HTML5 + CSS3 + JavaScript

Web Scraping: BeautifulSoup

Cache: TTLCache (customizado)

⭐ Funcionalidades Principais
Menu Hierárquico:

Escolha de jogo → Time → Dados (jogadores ou partidas).

Scraping em Tempo Real:

Dados atualizados diretamente da Liquipedia.

Cache Inteligente:

Reduz requisições à Liquipedia com TTL de 5 minutos.

Chat Interativo:

Edição/exclusão de mensagens em tempo real.

Temas Personalizáveis:

Modo claro/escuro com persistência via localStorage.

Fundo Dinâmico:

Imagem de fundo fixa com efeito de blur e overlay.

Integração com WhatsApp:

Widget para redirecionamento direto.

🛠️ Pré-requisitos
Python 3.8+

Pip (gerenciador de pacotes)

Navegador moderno (Chrome, Firefox, Edge)

📥 Instalação e Configuração
Passo 1: Clonar o Repositório
bash
git clone https://github.com/seu-usuario/furia-esports-bot.git
cd furia-esports-bot

Passo 2: Configurar Ambiente Virtual
bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows

Passo 3: Instalar Dependências
bash
pip install -r requirements.txt

Passo 4: Configurar Variáveis de Ambiente
Crie um arquivo .env na raiz do projeto:
python
FLASK_SECRET_KEY=sua_chave_secreta_aqui

Passo 5: Executar a Aplicação
bash
python app.py
Acesse: http://localhost.

💬 Uso do Bot
Iniciar o Bot:
Digite @FuriaBot no chat.

Navegar no Menu:

1. Escolha um jogo (CS2, Valorant, LoL)  
2. Selecione um time  
3. Escolha entre ver jogadores ou partidas  
Comandos Especiais:

0: Encerrar conversa.

@FuriaBot: Reiniciar o bot.

Exemplo de Fluxo:

@FuriaBot  
1 → 2 → 1  
Resposta: Lista de jogadores do time selecionado.  

📂 Estrutura do Projeto
furia-esports-bot/
├── static/
│   ├── css/                  # Estilos e temas
│   │   ├── style.css
│   │   └── themes.css
│   └── images/               # Imagens (ex: fundo)
├── templates/
│   └── index.html            # Interface do chat
├── venv/                     # Ambiente virtual
├── .env                      # Chaves secretas
├── app.py                    # Lógica principal
└── requirements.txt          # Dependências

🎨 Personalização
1. Alterar Imagem de Fundo
Substitua static/images/F98rnl8XwAAnrpY.jpg.

Ajuste o overlay em style.css:

css
body::before {
  background: rgba(0, 0, 0, 0.6); /* Opacidade */
}

2. Modificar Times
Atualize o dicionário GAME_TEAMS no app.py:

python
GAME_TEAMS = {
    'counterstrike': ['FURIA', 'FURIA Academy'],
    # ... outros jogos
}

3. Ajustar Cache
Edite o TTLCache em app.py:

python
cache = TTLCache(maxsize=50, ttl=600)  # 10 minutos

🤝 Contribuição
Faça um fork do projeto.

Crie uma branch: git checkout -b feature/nova-feature.

Commit suas mudanças: git commit -m 'Adicionei X'.

Push: git push origin feature/nova-feature.

Abra um Pull Request.

Diretrizes:

Mantenha o código documentado.

Teste alterações localmente antes de enviar.

📜 Licença
Distribuído sob a licença MIT. Veja LICENSE para detalhes.

🚧 Limitações e Próximos Passos
Limitações Atuais
Dependência da estrutura HTML da Liquipedia (pode quebrar com atualizações).

Cache em memória (não persistente entre reinicializações).

Roadmap Futuro
Adicionar suporte a mais jogos (ex: DOTA 2).

Implementar autenticação de usuários.

Adicionar notificações de partidas ao vivo.

Migrar para banco de dados (Redis/PostgreSQL).

Desenvolvido por Rafael Augusto Belo Silva - GitHub | LinkedIn - https://www.linkedin.com/in/rafaelbsdev/
🌟 Contribuições são bem-vindas!
