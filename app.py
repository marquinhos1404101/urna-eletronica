import os
import re
import time
from flask import Flask, render_template, request, session, redirect, url_for, jsonify

app = Flask(__name__)
# Chave nova a cada início do servidor: sessões antigas deixam de valer,
# então ao reiniciar o app o login com CPF é pedido de novo.
app.secret_key = os.urandom(32)
VERSAO = str(int(time.time()))  # evita CSS/JS antigo em cache


@app.context_processor
def injetar_versao():
    return {"v": VERSAO}


@app.after_request
def sem_cache(resp):
    resp.headers["Cache-Control"] = "no-store"
    return resp

# Sequência de votação: (id, título exibido, quantidade de dígitos)
ETAPAS = [
    ("deputado_estadual", "Deputado Estadual", 5),
    ("deputado_federal", "Deputado Federal", 4),
    ("senador_1", "Senador (1º voto)", 3),
    ("senador_2", "Senador (2º voto)", 3),
    ("governador", "Governador", 2),
    ("presidente", "Presidente", 2),
]

# Candidatos fictícios apenas para treinamento: cargo -> {numero: (nome, partido)}
SENADORES = {
    "400": ("Cid Gomes", "PSB"),
    "180": ("Luizianne", "REDE"),
    "445": ("Capitão Wagner", "UNIÃO"),
    "222": ("Alcides Fernandes", "PL"),
    "800": ("Catarina Matos", "UP"),
}
CANDIDATOS = {
    "deputado_estadual": {
        "22222": ("Tancredo dos Santos", "PL"),
        "50555": ("Gabriel Biologia", "PSOL"),
        "22022": ("Bella Carmelo", "PL"),
    },
    "deputado_federal": {
        "2222": ("Andre Fernandes", "PL"),
        "4077": ("Tainah Marinho", "PSB"),
        "1515": ("Yury do Paredão", "MDB"),
    },
    "senador_1": SENADORES,
    "senador_2": SENADORES,
    "governador": {
        "13": ("Elmano de Freitas", "PT"),
        "45": ("Ciro Gomes", "PSDB"),
        "14": ("Delegado Huggo", "MISSÃO"),
    },
    "presidente": {
        "22": ("Flavio Bolsonaro", "PT"),
        "13": ("Lula", "PT"),
        "70": ("Augusto Cury", "AVANTE"),
    },
}


def cpf_valido(cpf: str) -> bool:
    """Aceita qualquer combinação de 11 dígitos (CPF de treinamento)."""
    return len(cpf) == 11 and cpf.isdigit()


def logado() -> bool:
    return bool(session.get("cpf"))


@app.route("/")
def login():
    # A tela inicial SEMPRE pede o CPF: qualquer sessão anterior é encerrada.
    session.clear()
    return render_template("login.html")


@app.route("/entrar", methods=["POST"])
def entrar():
    dados = request.get_json(silent=True) or {}
    cpf = re.sub(r"\D", "", str(dados.get("cpf", "")))
    if not cpf_valido(cpf):
        return jsonify(ok=False, erro="Digite um CPF com 11 números."), 400
    session.clear()
    session["cpf"] = cpf
    session["etapa"] = 0
    session["votos"] = {}
    return jsonify(ok=True, destino=url_for("urna"))


@app.route("/urna")
def urna():
    if not logado():
        return redirect(url_for("login"))
    etapa = session.get("etapa", 0)
    if etapa >= len(ETAPAS):
        return redirect(url_for("fim"))
    cargo_id, titulo, digitos = ETAPAS[etapa]
    return render_template(
        "urna.html",
        cargo_id=cargo_id,
        titulo=titulo,
        digitos=digitos,
        posicao=etapa + 1,
        total=len(ETAPAS),
    )


@app.route("/api/candidato")
def api_candidato():
    """Consulta o candidato do cargo atual para o número digitado."""
    if not logado():
        return jsonify(erro="não autenticado"), 401
    etapa = session.get("etapa", 0)
    if etapa >= len(ETAPAS):
        return jsonify(erro="votação encerrada"), 400
    cargo_id, _, digitos = ETAPAS[etapa]
    numero = re.sub(r"\D", "", request.args.get("numero", ""))
    if len(numero) != digitos:
        return jsonify(completo=False)
    cand = CANDIDATOS[cargo_id].get(numero)
    if cand:
        return jsonify(completo=True, valido=True, nome=cand[0], partido=cand[1])
    return jsonify(completo=True, valido=False)


@app.route("/api/votar", methods=["POST"])
def api_votar():
    if not logado():
        return jsonify(ok=False, erro="não autenticado"), 401
    etapa = session.get("etapa", 0)
    if etapa >= len(ETAPAS):
        return jsonify(ok=True, destino=url_for("fim"))

    cargo_id, _, digitos = ETAPAS[etapa]
    dados = request.get_json(silent=True) or {}
    branco = bool(dados.get("branco"))
    numero = re.sub(r"\D", "", str(dados.get("numero", "")))

    if branco:
        voto = {"tipo": "branco"}
    elif len(numero) != digitos:
        return jsonify(ok=False, erro="Digite todos os números do candidato."), 400
    else:
        cand = CANDIDATOS[cargo_id].get(numero)
        if cand:
            voto = {"tipo": "candidato", "numero": numero, "nome": cand[0], "partido": cand[1]}
        else:
            voto = {"tipo": "nulo", "numero": numero}

    votos = session.get("votos", {})
    votos[cargo_id] = voto
    session["votos"] = votos
    session["etapa"] = etapa + 1

    destino = url_for("urna") if session["etapa"] < len(ETAPAS) else url_for("fim")
    return jsonify(ok=True, destino=destino)


@app.route("/fim")
def fim():
    if not logado():
        return redirect(url_for("login"))
    if session.get("etapa", 0) < len(ETAPAS):
        return redirect(url_for("urna"))
    resumo = [(titulo, session["votos"].get(cid)) for cid, titulo, _ in ETAPAS]
    return render_template("fim.html", resumo=resumo)


@app.route("/sair")
def sair():
    session.clear()
    return redirect(url_for("login"))


if __name__ == "__main__":
    app.run(debug=True)
