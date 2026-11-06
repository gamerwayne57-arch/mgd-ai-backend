from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import requests
import json, os, re, unicodedata, io, asyncio
import edge_tts
from bs4 import BeautifulSoup

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
MODELO_TEXTO = "openai/gpt-oss-120b"
MODELO_VISAO = "qwen/qwen3.8-27b" 
VOZ_NEURAL = "pt-BR-FranciscaNeural"

memoria_longa = []

# MEMÓRIA PÚBLICA PARA TODOS OS ITENS DO CATÁLOGO
site_data = {
    "mgd_ai_beta": {"likes": 0, "dislikes": 0, "comments": []},
    "site": {"likes": 0, "dislikes": 0, "comments": []},
    "app": {"likes": 0, "dislikes": 0, "comments": []},
    "jogo": {"likes": 0, "dislikes": 0, "comments": []},
    "outros": {"likes": 0, "dislikes": 0, "comments": []}
}

@app.route('/', methods=['GET'])
def home():
    return "Servidor MGD AI V94 (Web) está ONLINE! 🚀"

@app.route('/reactions/<item_id>', methods=['GET'])
def get_reactions(item_id):
    if item_id not in site_data:
        site_data[item_id] = {"likes": 0, "dislikes": 0, "comments": []}
    return jsonify(site_data[item_id])

@app.route('/react/<item_id>', methods=['POST'])
def react(item_id):
    dados = request.json
    acao = dados.get("action")
    if item_id not in site_data:
        site_data[item_id] = {"likes": 0, "dislikes": 0, "comments": []}
    
    if acao == "like": site_data[item_id]["likes"] += 1
    elif acao == "dislike": site_data[item_id]["dislikes"] += 1
    return jsonify(site_data[item_id])

@app.route('/comment/<item_id>', methods=['POST'])
def add_comment(item_id):
    dados = request.json
    user = dados.get("user", "Anonimo")
    text = dados.get("text", "")
    if item_id not in site_data:
        site_data[item_id] = {"likes": 0, "dislikes": 0, "comments": []}
    
    if text: site_data[item_id]["comments"].append({"user": user, "text": text})
    return jsonify(site_data[item_id])

@app.route('/chat', methods=['POST'])
def chat():
    dados = request.json
    if not dados: return jsonify({"error": "Nenhum dado recebido"}), 400

    pergunta = dados.get("message", "")
    chave_groq = dados.get("apiKey")
    historico = dados.get("history", [])
    imagem_base64 = dados.get("image")

    if not chave_groq: return jsonify({"error": "A chave Groq não foi enviada."}), 400

    global memoria_longa

    if re.match(r"^(?:lembra-te|lembre-se|guarda|memoriza)\s+que\s+(.+)$", pergunta, re.IGNORECASE):
        info = re.match(r"^(?:lembra-te|lembre-se|guarda|memoriza)\s+que\s+(.+)$", pergunta, re.IGNORECASE).group(1).strip()
        if info not in memoria_longa:
            memoria_longa.append(info)
            return jsonify({"reply": f"Memória guardada: {info}"})
        return jsonify({"reply": "Já tenho essa informação guardada."})

    urls = re.findall(r'(https?://[^\s]+)', pergunta)
    if urls and not imagem_base64:
        try:
            res = requests.get(urls[0], timeout=10, headers={'User-Agent': 'Mozilla/5.0'})
            soup = BeautifulSoup(res.text, 'html.parser')
            for script in soup(["script", "style"]): script.decompose()
            texto_site = soup.get_text(separator=' ', strip=True)[:3000]
            pergunta = f"O utilizador enviou o link {urls[0]}. Conteúdo: {texto_site}\n\nResponda: {pergunta}"
        except Exception:
            pass

    instrucao_sistema = (
        "Es a MGD AI, a inteligencia artificial oficial e assistente geral da MGD REDLINE. "
        "O teu criador e Wayne Matimbe, tambem conhecido como CEO Wayne, fundador da MGD REDLINE. "
        "A MGD REDLINE e uma empresa focada em tecnologia e jogos. "
        "REGRA DE FORMATAÇÃO OBRIGATÓRIA: NUNCA uses asteriscos (**) para destacar palavras ou colocar negrito. Escreve o texto normal e limpo. "
        "Usa blocos de codigo Markdown (```) APENAS para codigo de programacao real. "
        "NUNCA coloques respostas normais dentro de blocos de codigo ou entre crases (`). Responde sempre em texto puro, a menos que seja codigo."
    )
    if memoria_longa: instrucao_sistema += "\n\nMEMÓRIA: " + ", ".join(memoria_longa)

    mensagens = [{"role": "system", "content": instrucao_sistema}]
    for msg in historico[-10:]: mensagens.append(msg)

    if imagem_base64:
        mensagens.append({"role": "user", "content": [{"type": "text", "text": pergunta}, {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{imagem_base64}"}}]})
        modelo_usado = MODELO_VISAO
    else:
        mensagens.append({"role": "user", "content": pergunta})
        modelo_usado = MODELO_TEXTO

    headers = {"Authorization": f"Bearer {chave_groq}", "Content-Type": "application/json"}
    data = {"model": modelo_usado, "messages": mensagens, "temperature": 0.6, "max_tokens": 2048}

    try:
        response = requests.post(GROQ_URL, headers=headers, json=data, timeout=30)
        if response.status_code != 200: return jsonify({"error": "Erro na API Groq."}), 400
        return jsonify({"reply": response.json()["choices"][0]["message"]["content"]})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/tts', methods=['POST'])
def tts():
    dados = request.json
    texto = dados.get("text")
    if not texto: return jsonify({"error": "Texto vazio"}), 400

    try:
        async def gerar_audio():
            communicate = edge_tts.Communicate(texto, VOZ_NEURAL)
            audio_data = b""
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    audio_data += chunk["data"]
            return audio_data

        audio_bytes = asyncio.run(gerar_audio())
        return send_file(io.BytesIO(audio_bytes), mimetype="audio/mpeg")
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)