"""Py Grand Strategy Chronicles.

Um jogo de estratégia em texto inspirado em grandes simuladores históricos.
O foco desta versão é um sistema populacional mais rico: cada província tem
classes sociais, comida, prosperidade, autonomia, lealdade e revolta.
"""

from __future__ import annotations

import random
import time
from dataclasses import dataclass, field
from typing import Callable


PAUSA = 0.7


@dataclass
class Populacao:
    """Representa grupos sociais em milhares de habitantes."""

    camponeses: float
    artesoes: float
    burgueses: float
    nobres: float

    @property
    def total(self) -> float:
        return self.camponeses + self.artesoes + self.burgueses + self.nobres

    @property
    def forca_trabalho(self) -> float:
        return self.camponeses * 0.62 + self.artesoes * 0.74 + self.burgueses * 0.45

    def perdas(self, percentual: float) -> float:
        """Aplica perdas proporcionais e devolve o total perdido."""
        percentual = max(0.0, min(percentual, 0.95))
        antes = self.total
        self.camponeses *= 1 - percentual
        self.artesoes *= 1 - percentual
        self.burgueses *= 1 - percentual
        self.nobres *= 1 - percentual
        return antes - self.total

    def migrar_para(self, destino: "Populacao", pessoas: float) -> float:
        """Move pessoas, preservando aproximadamente a composição social."""
        pessoas = max(0.0, min(pessoas, self.total * 0.25))
        if self.total <= 0 or pessoas <= 0:
            return 0.0

        proporcao = pessoas / self.total
        for grupo in ("camponeses", "artesoes", "burgueses", "nobres"):
            migrantes = getattr(self, grupo) * proporcao
            setattr(self, grupo, getattr(self, grupo) - migrantes)
            setattr(destino, grupo, getattr(destino, grupo) + migrantes)
        return pessoas


@dataclass
class Provincia:
    nome: str
    populacao: Populacao
    fertilidade: float
    infraestrutura: int
    autonomia: int
    lealdade: int
    comida: float
    prosperidade: int = 50
    inquietacao: int = 0
    devastacao: int = 0
    ocupada: bool = False

    def capacidade_comida(self) -> float:
        modificador = 1 + self.infraestrutura * 0.08 + self.prosperidade / 250
        penalidade = 1 - self.devastacao / 120
        return max(0, self.populacao.camponeses * self.fertilidade * modificador * penalidade)

    def consumo_comida(self) -> float:
        return self.populacao.total * 0.82

    def receita_base(self) -> float:
        autonomia = 1 - self.autonomia / 100
        devastacao = 1 - self.devastacao / 100
        economia = (
            self.populacao.camponeses * 0.24
            + self.populacao.artesoes * 0.72
            + self.populacao.burgueses * 1.15
            + self.populacao.nobres * 0.38
        )
        return max(0, economia * autonomia * devastacao * (0.7 + self.prosperidade / 100))

    def manpower_anual(self) -> float:
        lealdade = 0.55 + self.lealdade / 200
        return max(0, self.populacao.camponeses * 0.018 * lealdade * (1 - self.devastacao / 100))

    def risco_revolta(self, estabilidade_nacional: int, legitimidade: int) -> int:
        fome = max(0, int((self.consumo_comida() - self.comida) / max(1, self.consumo_comida()) * 35))
        return max(
            0,
            self.inquietacao
            + self.autonomia // 6
            + self.devastacao // 3
            + fome
            - estabilidade_nacional // 8
            - legitimidade // 10
            - self.lealdade // 8,
        )

    def resumo(self) -> str:
        return (
            f"{self.nome}: {self.populacao.total:.1f}k hab. "
            f"(C:{self.populacao.camponeses:.1f} A:{self.populacao.artesoes:.1f} "
            f"B:{self.populacao.burgueses:.1f} N:{self.populacao.nobres:.1f}) | "
            f"Comida {self.comida:.0f}/{self.consumo_comida():.0f} | "
            f"Prosperidade {self.prosperidade}% | Lealdade {self.lealdade}% | "
            f"Autonomia {self.autonomia}% | Inquietação {self.inquietacao}%"
        )


@dataclass
class Nacao:
    nome: str
    ouro: int
    exercito: float
    estabilidade: int
    legitimidade: int
    tecnologia: int
    provincias: list[Provincia] = field(default_factory=list)
    politica_populacional: str = "equilibrada"
    ano: int = 1444

    @property
    def populacao_total(self) -> float:
        return sum(provincia.populacao.total for provincia in self.provincias)

    @property
    def manpower(self) -> float:
        return sum(provincia.manpower_anual() for provincia in self.provincias)

    @property
    def receita_prevista(self) -> int:
        return int(sum(provincia.receita_base() for provincia in self.provincias))

    @property
    def manutencao_exercito(self) -> int:
        return int(self.exercito * 1.8)

    def mostrar_status(self) -> None:
        print("\n" + "=" * 72)
        print(f" RAIO-X DO {self.nome.upper()} — ANO {self.ano}")
        print(f" Tesouro: {self.ouro} ducados")
        print(f" População: {self.populacao_total:.1f}k habitantes")
        print(f" Exército: {self.exercito:.1f}k soldados | Recrutas/ano: {self.manpower:.1f}k")
        print(f" Estabilidade: {self.estabilidade}% | Legitimidade: {self.legitimidade}% | Tecnologia: {self.tecnologia}")
        print(f" Receita prevista: {self.receita_prevista} | Manutenção militar: {self.manutencao_exercito}")
        print(f" Política populacional: {self.politica_populacional}")
        print("-" * 72)
        for provincia in self.provincias:
            print(" • " + provincia.resumo())
        print("=" * 72)

    def cobrar_impostos(self, modo: str) -> None:
        if modo == "leve":
            ganho = int(self.receita_prevista * 0.75)
            self.ouro += ganho
            self.estabilidade = min(100, self.estabilidade + 2)
            for provincia in self.provincias:
                provincia.prosperidade = min(100, provincia.prosperidade + 1)
            print(f"\nImpostos leves renderam {ganho} ducados e aliviaram a pressão social.")
        elif modo == "normal":
            ganho = self.receita_prevista
            self.ouro += ganho
            print(f"\nA burocracia real recolheu {ganho} ducados em impostos ordinários.")
        else:
            ganho = int(self.receita_prevista * 1.45)
            self.ouro += ganho
            self.estabilidade = max(0, self.estabilidade - 7)
            for provincia in self.provincias:
                provincia.inquietacao = min(100, provincia.inquietacao + 6)
                provincia.lealdade = max(0, provincia.lealdade - 3)
            print(f"\nImpostos de guerra renderam {ganho} ducados, mas irritaram a população.")

    def recrutar(self) -> None:
        custo = 55
        recrutas = min(8.0, self.manpower)
        if self.ouro < custo:
            print("\nOuro insuficiente para organizar novos regimentos.")
            return
        if recrutas < 1:
            print("\nNão há recrutas disponíveis; a população rural já está esgotada.")
            return

        self.ouro -= custo
        self.exercito += recrutas
        for provincia in self.provincias:
            perda = provincia.manpower_anual() / max(0.1, self.manpower) * recrutas * 0.62
            provincia.populacao.camponeses = max(0, provincia.populacao.camponeses - perda)
            provincia.inquietacao = min(100, provincia.inquietacao + 2)
        print(f"\n{recrutas:.1f}k soldados foram recrutados ao custo de {custo} ducados.")

    def investir_provincia(self) -> None:
        provincia = escolher_provincia(self.provincias)
        if not provincia:
            return
        print("\n1. Estradas e celeiros (80 ouro): +infraestrutura, +estoque de comida")
        print("2. Oficinas urbanas (70 ouro): +artesãos, +prosperidade")
        print("3. Administração local (60 ouro): -autonomia, +lealdade")
        escolha = input("Investimento: ").strip()

        if escolha == "1" and self.ouro >= 80:
            self.ouro -= 80
            provincia.infraestrutura += 1
            provincia.comida += 45
            provincia.prosperidade = min(100, provincia.prosperidade + 4)
            print(f"\n{provincia.nome} recebeu estradas, celeiros e canais de irrigação.")
        elif escolha == "2" and self.ouro >= 70:
            self.ouro -= 70
            convertidos = min(provincia.populacao.camponeses * 0.04, 3.5)
            provincia.populacao.camponeses -= convertidos
            provincia.populacao.artesoes += convertidos
            provincia.prosperidade = min(100, provincia.prosperidade + 8)
            print(f"\nOficinas em {provincia.nome} atraíram {convertidos:.1f}k trabalhadores urbanos.")
        elif escolha == "3" and self.ouro >= 60:
            self.ouro -= 60
            provincia.autonomia = max(0, provincia.autonomia - 12)
            provincia.lealdade = min(100, provincia.lealdade + 10)
            provincia.inquietacao = max(0, provincia.inquietacao - 4)
            print(f"\nIntendentes reais reforçaram a autoridade central em {provincia.nome}.")
        else:
            print("\nInvestimento cancelado: escolha inválida ou ouro insuficiente.")

    def mudar_politica_populacional(self) -> None:
        print("\n1. Natalista: maior crescimento, maior consumo de comida")
        print("2. Urbana: migração para cidades, mais impostos, menos comida")
        print("3. Militarizada: mais recrutas, menor prosperidade")
        print("4. Equilibrada: bônus pequeno e sem grandes riscos")
        opcoes = {"1": "natalista", "2": "urbana", "3": "militarizada", "4": "equilibrada"}
        escolha = input("Nova política: ").strip()
        if escolha in opcoes:
            self.politica_populacional = opcoes[escolha]
            print(f"\nA política populacional agora é {self.politica_populacional}.")
        else:
            print("\nPolítica mantida.")

    def processar_ano(self) -> None:
        self.ouro -= self.manutencao_exercito
        if self.ouro < 0:
            self.estabilidade = max(0, self.estabilidade - 5)
            print("\nA dívida militar corrói a estabilidade do reino.")

        for provincia in self.provincias:
            producao = provincia.capacidade_comida()
            consumo = provincia.consumo_comida()
            provincia.comida += producao - consumo

            crescimento = 0.008 + self.estabilidade / 12000 + provincia.prosperidade / 15000
            if self.politica_populacional == "natalista":
                crescimento += 0.01
                provincia.comida -= provincia.populacao.total * 0.05
            elif self.politica_populacional == "urbana":
                migrantes = min(provincia.populacao.camponeses * 0.018, 2.2)
                provincia.populacao.camponeses -= migrantes
                provincia.populacao.artesoes += migrantes * 0.72
                provincia.populacao.burgueses += migrantes * 0.28
                provincia.prosperidade = min(100, provincia.prosperidade + 2)
            elif self.politica_populacional == "militarizada":
                crescimento -= 0.004
                provincia.prosperidade = max(0, provincia.prosperidade - 1)
                provincia.lealdade = min(100, provincia.lealdade + 1)

            if provincia.comida < 0:
                deficit = abs(provincia.comida)
                fome = min(0.09, deficit / max(1, consumo) * 0.16)
                mortos = provincia.populacao.perdas(fome)
                provincia.comida = 0
                provincia.inquietacao = min(100, provincia.inquietacao + int(8 + fome * 120))
                provincia.prosperidade = max(0, provincia.prosperidade - 4)
                print(f"\nFome em {provincia.nome}: {mortos:.1f}k habitantes morreram ou fugiram.")
            else:
                crescimento_real = min(0.035, crescimento)
                provincia.populacao.camponeses *= 1 + crescimento_real
                provincia.populacao.artesoes *= 1 + crescimento_real * 0.85
                provincia.populacao.burgueses *= 1 + crescimento_real * 0.75
                provincia.populacao.nobres *= 1 + crescimento_real * 0.35
                provincia.prosperidade = min(100, provincia.prosperidade + 1)
                provincia.inquietacao = max(0, provincia.inquietacao - 2)

            provincia.devastacao = max(0, provincia.devastacao - 5)
            risco = provincia.risco_revolta(self.estabilidade, self.legitimidade)
            if random.randint(1, 100) <= risco:
                revolta = max(1.0, provincia.populacao.total * random.uniform(0.015, 0.04))
                self.exercito = max(0, self.exercito - revolta * 0.45)
                provincia.inquietacao = min(100, provincia.inquietacao + 12)
                provincia.lealdade = max(0, provincia.lealdade - 10)
                provincia.devastacao = min(100, provincia.devastacao + 12)
                print(f"\nRevolta em {provincia.nome}! Milícias locais causaram {revolta * 0.45:.1f}k baixas.")

        self.estabilidade = max(0, min(100, self.estabilidade))
        self.legitimidade = max(0, min(100, self.legitimidade))
        self.ano += 1


def escolher_provincia(provincias: list[Provincia]) -> Provincia | None:
    for indice, provincia in enumerate(provincias, start=1):
        print(f"{indice}. {provincia.resumo()}")
    escolha = input("Escolha a província: ").strip()
    if escolha.isdigit() and 1 <= int(escolha) <= len(provincias):
        return provincias[int(escolha) - 1]
    print("Província inválida.")
    return None


def criar_nacao_jogador(nome: str) -> Nacao:
    return Nacao(
        nome=nome or "Império Bizantino",
        ouro=210,
        exercito=22,
        estabilidade=78,
        legitimidade=72,
        tecnologia=1,
        provincias=[
            Provincia("Capital Régia", Populacao(82, 18, 9, 2.2), 1.18, 2, 18, 78, 95, 62),
            Provincia("Vales Centrais", Populacao(110, 9, 3, 1.3), 1.34, 1, 31, 66, 120, 54),
            Provincia("Porto Livre", Populacao(48, 21, 16, 0.9), 0.92, 2, 37, 58, 70, 68),
        ],
    )


def criar_rival() -> Nacao:
    return Nacao(
        nome="Império Rival",
        ouro=260,
        exercito=28,
        estabilidade=82,
        legitimidade=76,
        tecnologia=1,
        provincias=[
            Provincia("Marcas do Norte", Populacao(95, 12, 5, 1.6), 1.12, 1, 26, 70, 90, 56),
            Provincia("Planícies do Rei", Populacao(125, 10, 4, 1.8), 1.28, 1, 24, 73, 115, 58),
            Provincia("Cidade de Ferro", Populacao(58, 24, 13, 1.1), 0.84, 2, 32, 64, 64, 69),
            Provincia("Fronteira Oriental", Populacao(72, 7, 2, 0.8), 1.04, 0, 43, 50, 61, 42),
        ],
    )


def evento_aleatorio(jogador: Nacao) -> None:
    eventos: list[tuple[str, Callable[[Nacao], None]]] = [
        (
            "Colheita excepcional aumenta os celeiros e a confiança popular.",
            lambda n: [setattr(p, "comida", p.comida + 35) for p in n.provincias],
        ),
        (
            "Panfletos sediciosos circulam nas cidades portuárias.",
            lambda n: [setattr(p, "inquietacao", min(100, p.inquietacao + 5)) for p in n.provincias],
        ),
        (
            "Médicos estrangeiros ensinam quarentenas e saneamento urbano.",
            lambda n: setattr(n, "estabilidade", min(100, n.estabilidade + 5)),
        ),
        (
            "Uma guilda mercantil financia manufaturas em troca de privilégios.",
            lambda n: setattr(n, "ouro", n.ouro + 55),
        ),
    ]
    texto, efeito = random.choice(eventos)
    print(f"\n[EVENTO] {texto}")
    efeito(jogador)


def declarar_guerra(jogador: Nacao, rival: Nacao) -> None:
    if not rival.provincias:
        print("\nO rival já foi derrotado.")
        return

    print(f"\n[GUERRA] {jogador.nome} marcha contra {rival.nome}!")
    time.sleep(PAUSA)
    poder_jogador = jogador.exercito * (0.55 + jogador.estabilidade / 140) * (1 + jogador.tecnologia * 0.08)
    poder_rival = rival.exercito * (0.55 + rival.estabilidade / 140) * (1 + rival.tecnologia * 0.08)
    poder_jogador *= random.uniform(0.78, 1.28)
    poder_rival *= random.uniform(0.78, 1.28)
    print(f"Força projetada — Você: {poder_jogador:.1f} | Rival: {poder_rival:.1f}")

    if poder_jogador >= poder_rival:
        alvo = rival.provincias.pop(random.randrange(len(rival.provincias)))
        alvo.devastacao = min(100, alvo.devastacao + random.randint(12, 28))
        alvo.autonomia = min(100, alvo.autonomia + 18)
        alvo.lealdade = max(0, alvo.lealdade - 20)
        alvo.inquietacao = min(100, alvo.inquietacao + 18)
        jogador.provincias.append(alvo)
        baixas = jogador.exercito * random.uniform(0.12, 0.28)
        jogador.exercito = max(0, jogador.exercito - baixas)
        jogador.ouro += 65
        jogador.legitimidade = min(100, jogador.legitimidade + 4)
        print(f"Vitória! {alvo.nome} foi anexada, mas chega devastada e desconfiada.")
        print(f"Saque: 65 ducados | Baixas: {baixas:.1f}k soldados.")
    else:
        baixas = jogador.exercito * random.uniform(0.25, 0.52)
        jogador.exercito = max(0, jogador.exercito - baixas)
        jogador.estabilidade = max(0, jogador.estabilidade - 16)
        jogador.legitimidade = max(0, jogador.legitimidade - 8)
        for provincia in jogador.provincias:
            provincia.inquietacao = min(100, provincia.inquietacao + 5)
        print("Derrota humilhante! O fracasso alimenta críticas contra a coroa.")
        print(f"Baixas: {baixas:.1f}k soldados.")


def acao_rival(rival: Nacao) -> None:
    rival.ouro += max(20, rival.receita_prevista - rival.manutencao_exercito)
    if rival.ouro >= 65 and random.random() < 0.55:
        rival.ouro -= 65
        rival.exercito += min(6.0, max(1.0, rival.manpower))
    rival.processar_ano()


def loop_principal() -> None:
    print("=" * 58)
    print(" BEM-VINDO AO PY-GRAND-STRATEGY CHRONICLES ")
    print(" População, comida, classes sociais e revoltas agora importam.")
    print("=" * 58)

    jogador = criar_nacao_jogador(input("Dê um nome ao seu Império: ").strip())
    rival = criar_rival()

    while True:
        jogador.mostrar_status()
        print(f"\n[ANO {jogador.ano}] O que deseja fazer, Vossa Majestade?")
        print("1. Cobrar impostos leves")
        print("2. Cobrar impostos normais")
        print("3. Cobrar impostos de guerra")
        print("4. Recrutar regimentos")
        print("5. Investir em uma província")
        print("6. Mudar política populacional")
        print("7. Declarar guerra ao rival")
        print("8. Passar o ano")
        print("9. Sair do jogo")
        opcao = input("Escolha uma ação: ").strip()

        if opcao == "1":
            jogador.cobrar_impostos("leve")
        elif opcao == "2":
            jogador.cobrar_impostos("normal")
        elif opcao == "3":
            jogador.cobrar_impostos("pesado")
        elif opcao == "4":
            jogador.recrutar()
        elif opcao == "5":
            jogador.investir_provincia()
        elif opcao == "6":
            jogador.mudar_politica_populacional()
        elif opcao == "7":
            declarar_guerra(jogador, rival)
        elif opcao == "8":
            print("\nO calendário avança; colheitas, nascimentos e intrigas seguem seu curso...")
        elif opcao == "9":
            print("\nObrigado por jogar!")
            break
        else:
            print("\nComando inválido!")
            continue

        if jogador.estabilidade <= 0 or jogador.populacao_total < 40:
            print("\nGAME OVER! Fome, revoltas e crise dinástica destruíram o império.")
            break
        if not rival.provincias:
            print("\nVITÓRIA SUPREMA! O maior rival foi integrado ao seu domínio.")
            break

        acao_rival(rival)
        jogador.processar_ano()
        if random.random() < 0.42:
            evento_aleatorio(jogador)
        time.sleep(PAUSA)


if __name__ == "__main__":
    loop_principal()
