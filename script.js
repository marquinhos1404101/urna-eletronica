// ---------- Utilidades ----------
const AVISO_SERVIDOR =
    "Servidor não encontrado. Rode 'python app.py' e acesse http://127.0.0.1:5000 " +
    "(não abra os arquivos .html direto nem pelo Live Server).";

async function postJSON(url, dados) {
    try {
        const resp = await fetch(url, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(dados),
        });
        const corpo = await resp.json();
        return { ok: resp.ok, corpo };
    } catch (e) {
        return { ok: false, corpo: { erro: AVISO_SERVIDOR } };
    }
}

// ---------- Tela de login ----------
const campoCpf = document.getElementById("cpf");
if (campoCpf) {
    const botao = document.getElementById("entrar");
    const erro = document.getElementById("erro");

    function mascara(valor) {
        const d = valor.replace(/\D/g, "").slice(0, 11);
        return d
            .replace(/^(\d{3})(\d)/, "$1.$2")
            .replace(/^(\d{3})\.(\d{3})(\d)/, "$1.$2.$3")
            .replace(/\.(\d{3})(\d)/, ".$1-$2");
    }

    campoCpf.addEventListener("input", () => {
        campoCpf.value = mascara(campoCpf.value);
        erro.textContent = "";
    });

    async function entrar() {
        const { ok, corpo } = await postJSON("/entrar", { cpf: campoCpf.value });
        if (ok && corpo.ok) {
            window.location.href = corpo.destino;
        } else {
            erro.textContent = corpo.erro || "Não foi possível entrar.";
        }
    }

    botao.addEventListener("click", entrar);
    campoCpf.addEventListener("keydown", (e) => {
        if (e.key === "Enter") entrar();
    });
}

// ---------- Tela da urna ----------
const areaNumeros = document.getElementById("numeros");
if (areaNumeros) {
    const total = parseInt(document.body.dataset.digitos, 10);
    if (!total) {
        // Página aberta sem o Flask (o {{ digitos }} não foi preenchido)
        window.location.href = "/";
    }
    const info = document.getElementById("info");

    // Cria uma caixa para cada dígito do cargo atual
    for (let i = 0; i < total; i++) {
        const caixa = document.createElement("div");
        caixa.className = "num";
        caixa.appendChild(document.createElement("p"));
        areaNumeros.appendChild(caixa);
    }
    const caixas = areaNumeros.querySelectorAll(".num");
    let digitos = "";
    let branco = false;
    let ocupado = false;

    function desenhar() {
        caixas.forEach((c, i) => {
            c.firstElementChild.textContent = branco ? "" : (digitos[i] || "");
        });
    }

    function mostrar(html, classe) {
        info.className = "info" + (classe ? " " + classe : "");
        info.innerHTML = html;
    }

    async function consultar() {
        const resp = await fetch("/api/candidato?numero=" + digitos);
        const d = await resp.json();
        if (!d.completo) return;
        if (d.valido) {
            mostrar(
                "<b>Nome:</b> " + d.nome + "<br><b>Partido:</b> " + d.partido,
                "valido"
            );
        } else {
            mostrar("NÚMERO ERRADO<br>VOTO NULO", "nulo");
        }
    }

    function limpar() {
        digitos = "";
        branco = false;
        mostrar("", "");
        desenhar();
    }

    function digitar(n) {
        if (branco || digitos.length >= total) return;
        digitos += n;
        desenhar();
        if (digitos.length === total) consultar();
    }

    document.querySelectorAll(".tecla").forEach((b) =>
        b.addEventListener("click", () => digitar(b.textContent.trim()))
    );

    document.getElementById("bra").addEventListener("click", () => {
        digitos = "";
        branco = true;
        desenhar();
        mostrar("VOTO EM BRANCO", "branco");
    });

    document.getElementById("can").addEventListener("click", limpar);

    async function confirmar() {
        if (ocupado) return;
        if (!branco && digitos.length !== total) {
            mostrar("Digite todos os números<br>ou vote em BRANCO.", "aviso");
            return;
        }
        ocupado = true;
        const { ok, corpo } = await postJSON("/api/votar", { numero: digitos, branco });
        if (ok && corpo.ok) {
            window.location.href = corpo.destino; // próximo cargo ou tela final
        } else {
            ocupado = false;
            mostrar(corpo.erro || "Erro ao confirmar.", "aviso");
        }
    }

    document.getElementById("conf").addEventListener("click", confirmar);

    // Suporte ao teclado físico
    document.addEventListener("keydown", (e) => {
        if (/^\d$/.test(e.key)) digitar(e.key);
        else if (e.key === "Enter") confirmar();
        else if (e.key === "Backspace" || e.key === "Escape") limpar();
    });
}
