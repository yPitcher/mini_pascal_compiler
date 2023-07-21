"""Analisador Léxico para a linguagem Mini-Pascal

Trabalho de Compiladores I do Curso de Ciência da Computação da
Universidade Católica de Santos.

Integrantes do Grupo 1:
    - Brenno de Carvalho Vaquette
    - Davi Oliveira Venâncio
    - Eduardo Vantini Gonçalves
    - Esther Siqueira da Silva

!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
-- Modo de Uso:
    Mostra o resultado na tela:
        lexer.py {filepath}
    Mostra o resultado na tela e o salva em um arquivo de texto:
        lexer.py {filepath} -s
    Apenas salva o resultado em um arquivo de texto:
        lexer.py {filepath} -ds

    Para ajuda use:
        lexer.py -h
        lexer.py --help
!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
"""

# DEFINIÇÃO DO VOCABULÁRIO DO MINI-PASCAL.
# Define o vocabulário minímo para o Mini-Pascal segundo o livro[1] e o 
# PDF do trabalho.
#
# Referências:
# [1] WELSH, Jim; MCKEAG, Michael. Structured System Programming. 1. ed.
#     Londres: Prentice Hall International, 1980. 324 p.

from dataclasses import dataclass
from typing import Pattern, List
import re
import argparse
import sys
import os
import datetime

letter = r'a-zA-Z'
digit = r'0-9'
letter_or_digit = rf'{letter}{digit}'

# Nomes retirados da pg.94-95 do livro[1].
operators = [
    ('+', "PLUS"),
    ('-', "MINUS"),
    ('*', "TIMES"),
    ('=', "EQOP"),
    ('<>', "NEOP"),
    ('<', "LTOP"),
    ('<=', "LEOP"),
    ('>=', 'GEOP'),
    ('>', "GTOP"),
    ('(', "LEFTPARENT"),
    (')', "RIGHTPARENT"),
    ('[', "LEFTBRACKET"),
    (']', "RIGHTBRACKET"),
    (':=', "BECOMES"),
    ('.', "PERIOD"),
    (',', "COMMA"),
    (';', "SEMICOLON"),
    (':', "COLON"),
    ('..', "THRU")
]

reserved_words = [
    'div',
    'or',
    'and',
    'not',
    'if',
    'then',
    'else',
    'of',
    'while',
    'do',
    'begin',
    'end',
    'read',
    'write',
    'var',
    'array',
    'function',
    'procedure',
    'program',
    'true',
    'false',
    'char',
    'integer',
    'boolean'
]

special_symbols = [*operators, *[(word, "RESERVEDWORD") for word in reserved_words]]


# FIM DA DEFINIÇÃO DO VOCABULÁRIO DO MINI-PASCAL.

# FUNÇÕES DE APOIO.


@dataclass
class Rule:
    """Armazena uma regra léxica da linguagem.

    Essa classe é utilizada para organizar o código e evitar o uso
    incorreto de dicionários ou grupos aleatórios.

    Attributes:
        symbol (str): O nome dado à regra, de forma mais legível e
            distinta.
        type (str): O grupo ao qual a regra pertence, seguindo o
            formalismo de Backus-Naur, e mais próximo ao PDF do trabalho.
        regex (Pattern): O padrão utilizado para definir a regra.
    """
    symbol: str
    type: str
    regex: Pattern

    def __str__(self):
        return f"RULE: SYMBOL=\'{self.symbol}\' | TYPE=\'{self.type}\'"


@dataclass
class Rules:
    """Guarda as regras da linguagem.

    Attributes:
        rules (List[Rule]): Lista contendo todas as regras da linguagem.

    """
    rules: List[Rule]

    def __iter__(self):
        return iter(self.rules)

    def add(self, rule: Rule) -> None:
        """Adiciona uma regra à lista de regras.

        Attributes:
            rule (Rule): A regra a ser adicionada.

        Raises:
            TypeError: Se o objeto fornecido não for uma instância da
                classe Rule.
        """
        if isinstance(rule, Rule):
            self.rules.append(rule)
        else:
            raise TypeError("O objeto não é uma instância da classe Rule.")


@dataclass
class Pos:
    """Armazena a posição de uma palavra dentro de um texto.

    Essa classe é usada para organizar e armazenar a posição de uma
    palavra em um texto de forma estruturada.

    Attributes:
        lin (int): Número da linha onde a palavra está localizada.
        col (int): Número da coluna onde a palavra está localizada.
    """
    lin: int
    col: int


@dataclass
class Token:
    """Representa um token léxico em um texto.

    Essa classe é usada para armazenar informações sobre um token
    léxico, incluindo o lexema, a posição no texto, a regra associada
    e uma flag de erro indicando se o token não foi reconhecido por
    alguma regra.

    Attributes:
        lexeme (str): O lexema do token.
        pos (Pos): A posição do token no código fonte.
        rule (Rule): A regra associada ao token, se receber um valor
            None indica um erro, pois não foi reconhecido por nenhuma
            regra.

    Methods:
        __str__(): Retorna uma representação em string do token.
    """
    lexeme: str
    pos: Pos
    rule: Rule | None

    def __str__(self):
        return (
            f"TOKEN: {self.lexeme} | POS: line={self.pos.lin} "
            f"column={self.pos.col} | TYPE: {self.rule.type}"
        )


@dataclass
class Output:
    """Armazena os dados de saída.

    Armazena os resultados do analisador léxico para serem usados em um
    arquivo ou na saída do terminal.

    Attributes:
        line_count (int): Quantidade de linhas no arquivo fonte original.
        largest_lexeme_size (int): Tamanho do maior lexeme a ser
            mostrado, usado para fins de formatação na saída do terminal.
        largest_column_size (int): Maior posição na coluna de um token
            em uma linha.
        largest_type_size (int): Tamanho da maior palavra que compõe o
            tipo específico de um token.
        largest_group_size (int): Tamanho da maior palavra que compõe o
            grupo de um token.
        filename (str): Nome do arquivo do código fonte.
        tokens (List[Token]): Resultado do analisador léxico.
    """
    line_count: int
    largest_lexeme_size: int
    largest_column_size: int
    largest_type_size: int
    largest_group_size: int
    filename: str
    tokens: List[Token]

    def __iter__(self):
        return iter(self.tokens)


# FIM DAS FUNÇÕES DE APOIO.

# DEFINIÇÃO DA GRAMÁTICA
#
# Com base no livro[1] algumas modificações foram feitas na gramática
# passada no PDF do trabalho, são elas:
#
# - <constant> - Este símbolo não foi tratado pelo analisador léxico,
#    logo não irá aparecer nos resultados da tabela final, no livro é
#    mostrado que possui uma distinção entre os tipos de constantes,
#    este símbolo (<constant>) será adicionado no analisador sintático
#    (como mostrado no livro, pg.87-88) ao qual terá competência para
#    decidir quais tipos de constantes descritas pelo léxico irá aceitar
#    baseado na sintaxe que está analisando.
# - <constant identifier> - Este símbolo também não será tratado pelo
#    analisador léxico, no livro(pg.44) é demonstrado que este símbolo
#    é o único identificador constante em Mini-Pascal, ao qual se refere
#    ao valor booleano (true, false), como esses foram tratados como
#    <special symbol> não haverá necessidade do léxico trata-lo
#    individualmente, novamente será tratado pelo analisador sintático
#    como mostrado no livro(pg.87-88).
# - <letter>,<digit>,<letter or digit> - Serão usados apenas para compor
#    outros símbolos, já que se fossem tratados como símbolos da
#    gramática propriamente ditos, ou não seriam atingidos pela
#    hierarquia, ou seriam sempre escolhidos para descrever tudo no
#    código fonte.
#
# Ou seja os símbolos escolhidos para o analisador léxico tratar foram
# (ordenados hierarquicamente):
#
# - <special symbol>
# - <character constant>
# - <integer constant>
# - <identifier>


rules_arr = [
    *[Rule(name, "<special symbol>", re.compile(re.escape(op))) for (op, name) in operators],
    *[Rule(f"{word.upper()}", "<special symbol>", re.compile(word)) for word in reserved_words],
    Rule("CHARCONST", "<character constant>",
         re.compile(rf'\'[{letter_or_digit}]\'|\"[{letter_or_digit}\s]+\"')),
    Rule("INTCONST", "<integer constant>", re.compile(fr'[{digit}]+')),
    Rule("IDENT", "<identifier>", re.compile(fr'[{letter}][{letter_or_digit}]*')),
    Rule("SPACE", "<space>", re.compile(r'\s+'))
]

rules = Rules(rules_arr)


# FIM DA DEFINIÇÃO DA GRAMÁTICA

# ANALISADOR LÉXICO

class Lexer:
    """Realiza a análise léxica de um código-fonte.

    Attributes:
        source (str): O código-fonte a ser analisado.
        rules (List[Rule]): Lista contendo as regras léxicas a serem
            aplicadas.
        filepath (str): Retornado junto com o Output pois pode ser util
            em algumas funções de saída.

    Methods:
        analyze() -> Output: Realiza a análise léxica e retorna a
            tabela de tokens.
    """

    def __init__(self, source_code: str, rules: List[Rule], filepath: str):
        self.source = source_code
        self.rules = rules
        self.filepath = filepath

    def _filename(self) -> str:
        filename_extension = os.path.basename(self.filepath)
        filename = os.path.splitext(filename_extension)[0]

        return filename

    def analyze(self) -> Output:
        """Realiza a análise léxica do código-fonte.

        Returns:
            Output: A tabela de tokens gerada durante a análise
                léxica.
        """
        table = []
        lines = self.source.split('\n')

        # Variáveis para formatação do texto
        largest_lexeme_found_sz = 0
        largest_column_pos = 0
        largest_group_sz = 0
        largest_type_sz = 0

        error_found: bool = False

        for line_idx, line in enumerate(lines):
            column = 0
            while column < len(line) and not error_found:
                for rule in self.rules:
                    regex_match = rule.regex.match(line, pos=column)
                    if regex_match:
                        lexeme = regex_match.group(0)

                        # Para usar na formatação da saída
                        if len(lexeme) > largest_lexeme_found_sz:
                            largest_lexeme_found_sz = len(lexeme)
                        if (column + 1) > largest_column_pos:
                            largest_column_pos = column + 1
                        if len(rule.type) > largest_type_sz:
                            largest_type_sz = len(rule.type)
                        if len(rule.symbol) > largest_group_sz:
                            largest_group_sz = len(rule.symbol)

                        if rule.symbol != "SPACE":
                            token = Token(lexeme, Pos(line_idx + 1, column + 1), rule)
                            table.append(token)
                        column += len(lexeme)
                        break
                else:
                    token = Token(
                        str(line[column]),
                        Pos(line_idx + 1, column + 1),
                        None)
                    table.append(token)
                    error_found = True

        return Output(len(lines),
                      largest_lexeme_found_sz,
                      largest_column_pos,
                      largest_type_sz,
                      largest_group_sz,
                      self._filename(),
                      table)


# FIM DO ANALISADOR LÉXICO

# LEITOR DE ARQUIVO


def fileread(filepath: str) -> str:
    if os.path.isdir(filepath):
        sys.stderr.write(f"O caminho passado `{filepath}` é uma PASTA não um ARQUIVO!")
        sys.exit(3)

    try:
        with open(filepath, 'r') as f:
            data = f.read()
    except FileNotFoundError:
        sys.stderr.write(f"O arquivo `{filepath}` não foi encontrado!")
        sys.exit(2)
    except PermissionError:
        sys.stderr.write(f"Sem permissão para abrir o arquivo `{filepath}`.")
        sys.exit(4)
    except IOError:
        sys.stderr.write(f"Houve um erro na leitura/escrita do arquivo `{filepath}`.")
        sys.exit(5)

    return data


# FIM DO LEITOR DE ARQUIVO

# FUNÇÕES DE SAÍDA


def _token_str(token: Token, output: Output) -> str:
    """Transforma um token em uma string organizada

    Attributes:
        token (Token): Token a ser organizado em uma string.
        output (Output): Dados da saída do analisador léxico, usado para
            organizar as colunas da saída.
    
    Returns:
        (str) - Contendo os dados organizados do token prontos para
            serem usado em algum tipo de saída.
    """
    lexeme_f = '\'' + token.lexeme + '\''

    if not token.rule:
        return (f"{str(token.pos.lin):<{len(str(output.line_count))}s}"
                f"[{str(token.pos.col):>{len(str(output.largest_column_size))}s}]: "
                f"{lexeme_f:^{output.largest_lexeme_size + 10}s} "
                f"{'**erro**':<{output.largest_group_size + 2}s} "
                f"{'ERRO':<{output.largest_type_size}s}")

    return (f"{str(token.pos.lin):<{len(str(output.line_count))}s}"
            f"[{str(token.pos.col):>{len(str(output.largest_column_size))}s}]: "
            f"{lexeme_f:^{output.largest_lexeme_size + 10}s} "
            f"{token.rule.symbol:<{output.largest_group_size + 2}s} "
            f"{token.rule.type:<{output.largest_type_size}s}")


def _table_columns_title(output: Output) -> str:
    """Monta os títulos das colunas da tabela de saída.

    Attributes:
        output (Output): Dados da saída do analisador léxico, usado para
            organizar as colunas da saída.
    
    Returns:
        (str) - Contendo os títulos da tabela de saída.
    """
    return (f"{'LIN[COL]':>{len(str(output.largest_column_size))}s}"
            f"{'LEXEMA':^{output.largest_lexeme_size + 9}s} "
            f"{'SÍMBOLO':<{output.largest_group_size + 2}s} "
            f"{'TIPO':<{output.largest_type_size}s}")


def _generate_tokens_str(output: Output) -> List[str]:
    """Gera uma lista com todos os tokens gerados pelo analisador léxico.

    Attributes:
        output (Output): Dados da saída do analisador léxico.

    Returns:
        tokens_str (List[str]): Lista contendo cada token gerado.
    """
    tokens_str = []
    for token in output.tokens:
        tokens_str.append(_token_str(token, output))

    return tokens_str


def _print_table(tokens_str: List[str], title: str) -> None:
    """Gera uma lista com todos os tokens gerados pelo analisador léxico.

    Attributes:
        tokens_str (List[str]): Lista com todos os tokens gerados pelo
            analisador léxico.
        title (str): string contendo a linha dos títulos da tabela a ser
            mostrada.
    """
    print(title)
    for token_str in tokens_str:
        print(token_str)


def _filename(original_filename: str) -> str:
    """Gera um nome único para o arquivo de saída.

    Attributes:
        original_filename (str): Nome do arquivo fonte lido inicialmente.
    
    Returns:
        filename (str): Nome único do arquivo para salvar a tabela.
    """
    while True:
        dt = datetime.datetime.now()
        dt_str = dt.strftime("%d-%m-%Y--%H-%M-%S-%f")
        filename = f"LEXER_{original_filename}_{dt_str}.txt"

        if not os.path.exists(filename):
            return filename


def _save_to_file(filename: str, tokens_str: List[str], title: str) -> None:
    """Salva a tabela em um arquivo.

    Attributes:
        filename (str): Nome do arquivo onde sera salvo a tabela.
        tokens_str (List[str]): Lista com todos os tokens gerados pelo
            analisador léxico.
        title (str): Linha contendo os títulos das colunas da tabela.
    """
    with open(filename, "w", encoding="utf-8") as f:
        f.write(title + '\n')
        for token_str in tokens_str:
            f.write(token_str + '\n')


def options(output: Output, display: bool = True, save: bool = False) -> None:
    """Trata as opções disponíveis para o usuário.

    Attributes:
        output (Output): Dados gerados pelo analisador léxico.
        display (bool): Valor que define se será ou não mostrado a tabela
            na saída do terminal. O PADRÃO é TRUE, que mostra o resultado
            na tela.
        save (bool): Valor que define se a tabela será ou não salva em
            um arquivo. O PADRÃO é FALSE, que não salva em um arquivo.
    """
    tokens_str = _generate_tokens_str(output)

    title = _table_columns_title(output)

    if display:
        _print_table(tokens_str, title)
    if save:
        filename = _filename(output.filename)
        _save_to_file(filename, tokens_str, title)


# FIM DAS FUNÇÕES DE SAÍDA

def main():
    parser = argparse.ArgumentParser(
        description="Um analisador léxico para o Mini-Pascal",
    )

    parser.add_argument("-d", "--do-not-display", dest="do_not_display",
                        action="store_true", default=False,
                        help="disabilita a escrita da tabela no terminal")
    parser.add_argument("-s", "--save", dest="save", default=False,
                        action="store_true",
                        help="salva o resultado em um arquivo")
    parser.add_argument(dest="filepath", nargs="?",
                        help="o arquivo a passar pelo analisador")

    args = parser.parse_args()

    if args.filepath:
        data = fileread(args.filepath)
        lexer = Lexer(data, rules, args.filepath)

        output = lexer.analyze()

        if args.do_not_display and args.save:
            options(output, False, True)
        elif args.save:
            options(output, save=True)
        else:
            options(output)

    else:
        sys.stderr.write("O campo `filename` não foi passado. Por favor informe o "
                         "arquivo a ser lido pelo analisador léxico!")
        sys.exit(1)


if __name__ == "__main__":
    main()
