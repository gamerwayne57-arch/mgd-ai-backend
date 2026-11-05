from flask import Flask, request, jsonify
from flask_cors import CORS
import requests

app = Flask(__name__)
# CORS permite que o teu site (seja lá onde estiver) fale com este servidor
CORS(app, resources={r"/*": {"origins": "*"}})

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
MODELO_TEXTO = "openai/gpt-oss-120b" # Modelo topo de gama que já testaste

@app.route('/', methods=['GET'])
def home():
    return "Servidor MGD AI V94 está ONLINE! 🚀"

@app.route('/chat', methods=['POST'])
def chat():
    dados = request.json
    
    if not dados:
        return jsonify({"error": "Nenhum dado recebido"}), 400

    pergunta = dados.get("message")
    chave_groq = dados.get("apiKey") # A chave do utilizador
    historico = dados.get("history", [])

    if not chave_groq:
        return jsonify({"error": "A chave Groq não foi enviada."}), 400

    # Instrução de sistema baseada no teu main.py
    instrucao_sistema = (
        "Es a MGD AI, a inteligencia artificial oficial e assistente geral da MGD REDLINE. "
        "O teu criador e Wayne Matimbe, tambem conhecido como CEO Wayne. "
        "Responde no idioma usado pelo utilizador; se ele escrever em portugues, usa portugues natural e claro com acentuação correta. "
        "Nao inventes informacoes. Se nao souberes, diz claramente. "
        "Formata codigo com blocos Markdown de tres crases e identifica a linguagem."
    )

    # Prepara o histórico + a nova mensagem
    mensagens = [{"role": "system", "content": instrucao_sistema}]
    
    # Adiciona o histórico anterior (se existir)
    for msg in historico:
        mensagens.append(msg)
        
    # Adiciona a pergunta atual
    mensagens.append({"role": "user", "content": pergunta})

    headers = {
        "Authorization": f"Bearer {chave_groq}",
        "Content-Type": "application/json"
    }

    data = {
        "model": MODELO_TEXTO,
        "messages": mensagens,
        "temperature": 0.6,
        "max_tokens": 2048
    }

    try:
        response = requests.post(GROQ_URL, headers=headers, json=data, timeout=30)
        
        if response.status_code != 200:
            detalhe = response.json().get("error", {}).get("message", "Erro desconhecido")
            return jsonify({"error": f"Erro na Groq: {detalhe}"}), 400
            
        resultado = response.json()
        texto_ia = resultado["choices"][0]["message"]["content"]
        
        return jsonify({"reply": texto_ia})

    except Exception as e:
        return jsonify({"error": f"Erro no Servidor Python: {str(e)}"}), 500

if __name__ == '__main__':
    # Roda na porta 8080
    app.run(host='0.0.0.0', port=8080)