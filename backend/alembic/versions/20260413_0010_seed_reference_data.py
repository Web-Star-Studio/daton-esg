"""seed reference data (gri standards, ods, captacao matriz, indicator templates)

The literals below are extracted from
``docs/Documentos de Instrução/03) Diretrizes para a configuração de IA -
Relatórios de Sustentabilidade.xlsx`` via
``backend/scripts/extract_reference_seed.py``. Regenerate only when the source
spreadsheet changes.
"""

import sqlalchemy as sa

from alembic import op

revision = "20260413_0010"
down_revision = "20260413_0009"
branch_labels = None
depends_on = None


GRI_STANDARDS = [
    {
        "code": "GRI 2-1",
        "family": "2",
        "standard_text": "Detalhes organizacionais (nome, natureza das atividades, marcas, produtos, serviços, sede, países de operação)",
    },
    {
        "code": "GRI 2-2",
        "family": "2",
        "standard_text": "Entidades incluídas no relatório e escopo do relatório (ex: atividades da sede, escritórios, fábricas, centros de distribuição)",
    },
    {
        "code": "GRI 2-3",
        "family": "2",
        "standard_text": "Período de relato, frequência de relato e ponto de contato para perguntas sobre o relatório",
    },
    {
        "code": "GRI 2-4",
        "family": "2",
        "standard_text": "Reafirmação de informações (se houve reedição de dados ou informações)",
    },
    {
        "code": "GRI 2-5",
        "family": "2",
        "standard_text": "Asseguração externa (se o relatório foi verificado por um assegurador externo)",
    },
    {
        "code": "GRI 2-6",
        "family": "2",
        "standard_text": "Mudanças significativas na organização e sua cadeia de suprimentos (ex: número de fábricas, atividades de negócio, mudanças como desinvestimentos)",
    },
    {
        "code": "GRI 2-7",
        "family": "2",
        "standard_text": "Estrutura e composição do mais alto órgão de governança",
    },
    {
        "code": "GRI 2-8",
        "family": "2",
        "standard_text": "Declaração de propósito, valores e estratégia",
    },
    {
        "code": "GRI 2-9",
        "family": "2",
        "standard_text": "Papel do mais alto órgão de governança na supervisão da gestão de impactos",
    },
    {
        "code": "GRI 2-10",
        "family": "2",
        "standard_text": "Delegação de responsabilidade pela gestão de impactos",
    },
    {
        "code": "GRI 2-11",
        "family": "2",
        "standard_text": "Papel do mais alto órgão de governança na supervisão da estratégia de sustentabilidade",
    },
    {
        "code": "GRI 2-12",
        "family": "2",
        "standard_text": "Papel do mais alto órgão de governança na supervisão do relato de sustentabilidade (ex: avaliação trimestral de conquistas, relatórios a acionistas)",
    },
    {"code": "GRI 2-13", "family": "2", "standard_text": "Conflitos de interesse"},
    {
        "code": "GRI 2-14",
        "family": "2",
        "standard_text": "Comunicação de preocupações críticas",
    },
    {
        "code": "GRI 2-15",
        "family": "2",
        "standard_text": "Natureza e número de preocupações críticas levantadas",
    },
    {
        "code": "GRI 2-16",
        "family": "2",
        "standard_text": "Mecanismos para buscar aconselhamento e levantar preocupações",
    },
    {
        "code": "GRI 2-17",
        "family": "2",
        "standard_text": "Conhecimento coletivo do mais alto órgão de governança sobre tópicos de sustentabilidade",
    },
    {
        "code": "GRI 2-18",
        "family": "2",
        "standard_text": "Avaliação do desempenho do mais alto órgão de governança",
    },
    {
        "code": "GRI 2-19",
        "family": "2",
        "standard_text": "Políticas de remuneração (incluindo ligação a desempenho ESG)",
    },
    {
        "code": "GRI 2-20",
        "family": "2",
        "standard_text": "Processo para determinar a remuneração",
    },
    {
        "code": "GRI 2-21",
        "family": "2",
        "standard_text": "Relação de remuneração anual total",
    },
    {
        "code": "GRI 2-22",
        "family": "2",
        "standard_text": "Declaração sobre a estratégia de desenvolvimento sustentável (ex: Plano de Ação de Crescimento)",
    },
    {
        "code": "GRI 2-23",
        "family": "2",
        "standard_text": "Compromissos de política (ex: direitos humanos, trabalho, meio ambiente, anticorrupção)",
    },
    {
        "code": "GRI 2-24",
        "family": "2",
        "standard_text": "Incorporação de compromissos de política",
    },
    {
        "code": "GRI 2-25",
        "family": "2",
        "standard_text": "Processos para remediar impactos negativos",
    },
    {"code": "GRI 2-26", "family": "2", "standard_text": "Mecanismos de reclamação"},
    {
        "code": "GRI 2-27",
        "family": "2",
        "standard_text": "Conformidade com os princípios do Pacto Global das Nações Unidas",
    },
    {
        "code": "GRI 2-28",
        "family": "2",
        "standard_text": "Associação a associações e organizações",
    },
    {
        "code": "GRI 2-29",
        "family": "2",
        "standard_text": "Engajamento de stakeholders (ex: uso do AA1000 Stakeholder Engagement Standard)",
    },
    {"code": "GRI 2-30", "family": "2", "standard_text": "Acordos coletivos"},
    {
        "code": "GRI 3-1",
        "family": "3",
        "standard_text": "Processo para determinar tópicos materiais",
    },
    {"code": "GRI 3-2", "family": "3", "standard_text": "Lista de tópicos materiais"},
    {"code": "GRI 3-3", "family": "3", "standard_text": "Gestão de tópicos materiais"},
    {
        "code": "GRI 201-1",
        "family": "200",
        "standard_text": "Valor econômico direto gerado e distribuído",
    },
    {
        "code": "GRI 201-2",
        "family": "200",
        "standard_text": "Implicações financeiras e outros riscos e oportunidades devido às alterações climáticas",
    },
    {
        "code": "GRI 201-3",
        "family": "200",
        "standard_text": "Obrigações de planos de benefícios definidos e outros planos de aposentadoria",
    },
    {
        "code": "GRI 201-4",
        "family": "200",
        "standard_text": "Assistência financeira recebida do governo",
    },
    {
        "code": "GRI 202-1",
        "family": "200",
        "standard_text": "Relação do salário inicial padrão por gênero em comparação com o salário mínimo local",
    },
    {
        "code": "GRI 203-1",
        "family": "200",
        "standard_text": "Investimentos em infraestrutura e serviços apoiados",
    },
    {
        "code": "GRI 203-2",
        "family": "200",
        "standard_text": "Impactos econômicos indiretos significativos",
    },
    {
        "code": "GRI 204-1",
        "family": "200",
        "standard_text": "Proporção de gastos com fornecedores locais",
    },
    {
        "code": "GRI 205-1",
        "family": "200",
        "standard_text": "Operações avaliadas quanto a riscos relacionados à corrupção",
    },
    {
        "code": "GRI 205-2",
        "family": "200",
        "standard_text": "Comunicação e treinamento sobre políticas e procedimentos anticorrupção",
    },
    {
        "code": "GRI 205-3",
        "family": "200",
        "standard_text": "Incidentes confirmados de corrupção e ações tomadas",
    },
    {
        "code": "GRI 206-1",
        "family": "200",
        "standard_text": "Ações legais por comportamento anticompetitivo, antitruste e práticas de monopólio",
    },
    {"code": "GRI 207-1", "family": "200", "standard_text": "Abordagem fiscal"},
    {"code": "GRI 207-2", "family": "200", "standard_text": ""},
    {
        "code": "GRI 207-3",
        "family": "200",
        "standard_text": "Engajamento de stakeholders e gestão de preocupações relacionadas a impostos",
    },
    {"code": "GRI 207-4", "family": "200", "standard_text": "Relato país a país"},
    {
        "code": "GRI 301-1",
        "family": "300",
        "standard_text": "Materiais utilizados por peso ou volume",
    },
    {
        "code": "GRI 301-2",
        "family": "300",
        "standard_text": "Materiais de entrada reciclados utilizados",
    },
    {
        "code": "GRI 301-3",
        "family": "300",
        "standard_text": "Produtos recuperados e seus materiais de embalagem",
    },
    {
        "code": "GRI 302-1",
        "family": "300",
        "standard_text": "Consumo de energia dentro da organização",
    },
    {
        "code": "GRI 302-2",
        "family": "300",
        "standard_text": "Consumo de energia fora da organização",
    },
    {"code": "GRI 302-3", "family": "300", "standard_text": "Intensidade energética"},
    {
        "code": "GRI 302-4",
        "family": "300",
        "standard_text": "Reduções no consumo de energia",
    },
    {
        "code": "GRI 302-5",
        "family": "300",
        "standard_text": "Reduções nas necessidades de energia de produtos e serviços",
    },
    {
        "code": "GRI 303-1",
        "family": "300",
        "standard_text": "Interações com a água como recurso compartilhado",
    },
    {
        "code": "GRI 303-2",
        "family": "300",
        "standard_text": "Gestão dos impactos relacionados à descarga de água",
    },
    {"code": "GRI 303-3", "family": "300", "standard_text": "Captação de água"},
    {"code": "GRI 303-4", "family": "300", "standard_text": "Descarga de água"},
    {"code": "GRI 303-5", "family": "300", "standard_text": "Consumo de água"},
    {
        "code": "GRI 304-1",
        "family": "300",
        "standard_text": "Locais operacionais localizados dentro ou adjacentes a áreas protegidas e áreas de alto valor de biodiversidade fora de áreas protegidas",
    },
    {
        "code": "GRI 304-2",
        "family": "300",
        "standard_text": "Impactos significativos de atividades, produtos e serviços na biodiversidade",
    },
    {
        "code": "GRI 304-3",
        "family": "300",
        "standard_text": "Habitats protegidos ou restaurados",
    },
    {
        "code": "GRI 304-4",
        "family": "300",
        "standard_text": "Espécies da Lista Vermelha da IUCN e espécies da lista de conservação nacional com habitats em áreas afetadas por operações",
    },
    {
        "code": "GRI 305-1",
        "family": "300",
        "standard_text": "Emissões diretas de GEE (Escopo 1)",
    },
    {
        "code": "GRI 305-2",
        "family": "300",
        "standard_text": "Emissões indiretas de energia (Escopo 2)",
    },
    {
        "code": "GRI 305-3",
        "family": "300",
        "standard_text": "Outras emissões indiretas de GEE (Escopo 3)",
    },
    {
        "code": "GRI 305-4",
        "family": "300",
        "standard_text": "Intensidade das emissões de GEE",
    },
    {
        "code": "GRI 305-5",
        "family": "300",
        "standard_text": "Redução das emissões de GEE",
    },
    {
        "code": "GRI 305-6",
        "family": "300",
        "standard_text": "Emissões de substâncias que esgotam a camada de ozono (ODS)",
    },
    {
        "code": "GRI 305-7",
        "family": "300",
        "standard_text": "Óxidos de azoto (NOx), óxidos de enxofre (SOx) e outras emissões atmosféricas significativas",
    },
    {
        "code": "GRI 306-1",
        "family": "300",
        "standard_text": "Geração de resíduos e impactos significativos relacionados a resíduos",
    },
    {
        "code": "GRI 306-2",
        "family": "300",
        "standard_text": "Resíduos por tipo e método de descarte",
    },
    {
        "code": "GRI 306-3",
        "family": "300",
        "standard_text": "Derramamentos significativos",
    },
    {
        "code": "GRI 306-4",
        "family": "300",
        "standard_text": "Transporte de resíduos perigosos",
    },
    {
        "code": "GRI 306-5",
        "family": "300",
        "standard_text": "Corpos d'água afetados por descargas de água e escoamento",
    },
    {
        "code": "GRI 307-1",
        "family": "300",
        "standard_text": "Não conformidade com leis e regulamentos ambientais",
    },
    {
        "code": "GRI 401-1",
        "family": "400",
        "standard_text": "Novas contratações de funcionários e rotatividade de funcionários",
    },
    {
        "code": "GRI 401-2",
        "family": "400",
        "standard_text": "Benefícios fornecidos a funcionários em tempo integral que não são fornecidos a funcionários temporários ou de meio período",
    },
    {"code": "GRI 401-3", "family": "400", "standard_text": "Licença parental"},
    {
        "code": "GRI 402-1",
        "family": "400",
        "standard_text": "Períodos mínimos de aviso prévio em relação a mudanças operacionais",
    },
    {
        "code": "GRI 403-1",
        "family": "400",
        "standard_text": "Sistema de gestão de saúde e segurança ocupacional",
    },
    {
        "code": "GRI 403-2",
        "family": "400",
        "standard_text": "Identificação de perigos, avaliação de riscos e investigação de incidentes",
    },
    {
        "code": "GRI 403-3",
        "family": "400",
        "standard_text": "Serviços de saúde ocupacional",
    },
    {
        "code": "GRI 403-4",
        "family": "400",
        "standard_text": "Participação, consulta e comunicação dos trabalhadores sobre saúde e segurança ocupacional",
    },
    {
        "code": "GRI 403-5",
        "family": "400",
        "standard_text": "Treinamento de trabalhadores em saúde e segurança ocupacional",
    },
    {
        "code": "GRI 403-6",
        "family": "400",
        "standard_text": "Promoção da saúde do trabalhador",
    },
    {
        "code": "GRI 403-7",
        "family": "400",
        "standard_text": "Prevenção e mitigação de impactos na saúde e segurança ocupacional diretamente ligados por relações de negócios",
    },
    {
        "code": "GRI 403-8",
        "family": "400",
        "standard_text": "Trabalhadores cobertos por um sistema de gestão de saúde e segurança ocupacional",
    },
    {
        "code": "GRI 403-9",
        "family": "400",
        "standard_text": "Lesões relacionadas ao trabalho",
    },
    {
        "code": "GRI 403-10",
        "family": "400",
        "standard_text": "Doenças relacionadas ao trabalho",
    },
    {
        "code": "GRI 404-1",
        "family": "400",
        "standard_text": "Média de horas de treinamento por ano por funcionário",
    },
    {
        "code": "GRI 404-2",
        "family": "400",
        "standard_text": "Programas para aprimoramento de habilidades de funcionários e programas de assistência à transição",
    },
    {
        "code": "GRI 404-3",
        "family": "400",
        "standard_text": "Percentual de funcionários recebendo avaliações regulares de desempenho e desenvolvimento de carreira",
    },
    {
        "code": "GRI 405-1",
        "family": "400",
        "standard_text": "Diversidade de órgãos de governança e funcionários",
    },
    {
        "code": "GRI 405-2",
        "family": "400",
        "standard_text": "Relação do salário base e remuneração de mulheres para homens",
    },
    {
        "code": "GRI 406-1",
        "family": "400",
        "standard_text": "Incidentes de discriminação e ações corretivas tomadas",
    },
    {
        "code": "GRI 407-1",
        "family": "400",
        "standard_text": "Operações e fornecedores nos quais o direito à liberdade de associação e negociação coletiva pode estar em risco",
    },
    {
        "code": "GRI 408-1",
        "family": "400",
        "standard_text": "Operações e fornecedores com risco significativo de incidentes de trabalho infantil",
    },
    {
        "code": "GRI 409-1",
        "family": "400",
        "standard_text": "Operações e fornecedores com risco significativo de incidentes de trabalho forçado ou obrigatório",
    },
    {
        "code": "GRI 410-1",
        "family": "400",
        "standard_text": "Pessoal de segurança treinado em políticas ou procedimentos de direitos humanos",
    },
    {
        "code": "GRI 411-1",
        "family": "400",
        "standard_text": "Incidentes de violações dos direitos dos povos indígenas",
    },
    {
        "code": "GRI 412-1",
        "family": "400",
        "standard_text": "Operações que foram sujeitas a revisões de direitos humanos ou avaliações de impacto",
    },
    {
        "code": "GRI 412-2",
        "family": "400",
        "standard_text": "Treinamento de funcionários sobre políticas ou procedimentos de direitos humanos",
    },
    {
        "code": "GRI 412-3",
        "family": "400",
        "standard_text": "Acordos e contratos de investimento significativos que incluem cláusulas de direitos humanos ou que foram submetidos a triagem de direitos humanos",
    },
    {
        "code": "GRI 413-1",
        "family": "400",
        "standard_text": "Operações com engajamento da comunidade local, avaliações de impacto e programas de desenvolvimento",
    },
    {
        "code": "GRI 413-2",
        "family": "400",
        "standard_text": "Operações com impactos negativos significativos reais e potenciais nas comunidades locais",
    },
    {
        "code": "GRI 414-1",
        "family": "400",
        "standard_text": "Novos fornecedores que foram rastreados usando critérios sociais",
    },
    {
        "code": "GRI 414-2",
        "family": "400",
        "standard_text": "Impactos sociais negativos na cadeia de suprimentos e ações tomadas",
    },
    {"code": "GRI 415-1", "family": "400", "standard_text": "Contribuições políticas"},
    {
        "code": "GRI 416-1",
        "family": "400",
        "standard_text": "Avaliação dos impactos na saúde e segurança das categorias de produtos e serviços",
    },
    {
        "code": "GRI 416-2",
        "family": "400",
        "standard_text": "Incidentes de não conformidade relacionados aos impactos na saúde e segurança de produtos e serviços",
    },
    {
        "code": "GRI 417-1",
        "family": "400",
        "standard_text": "Requisitos para informações e rotulagem de produtos e serviços",
    },
    {
        "code": "GRI 417-2",
        "family": "400",
        "standard_text": "Incidentes de não conformidade relacionados a informações e rotulagem de produtos e serviços",
    },
    {
        "code": "GRI 417-3",
        "family": "400",
        "standard_text": "Incidentes de não conformidade relacionados a comunicações de marketing",
    },
    {
        "code": "GRI 418-1",
        "family": "400",
        "standard_text": "Reclamações fundamentadas sobre violações de privacidade do cliente e perdas de dados do cliente",
    },
    {
        "code": "GRI 419-1",
        "family": "400",
        "standard_text": "Não conformidade com leis e regulamentos na área social e econômica",
    },
]

ODS_GOALS = [
    {"ods_number": 1, "objetivo": "Erradicação da Pobreza"},
    {"ods_number": 2, "objetivo": "Fome Zero e Agricultura Sustentável"},
    {"ods_number": 3, "objetivo": "Saúde e Bem-Estar"},
    {"ods_number": 4, "objetivo": "Educação de Qualidade"},
    {"ods_number": 5, "objetivo": "Igualdade de Gênero"},
    {"ods_number": 6, "objetivo": "Água Potável e Saneamento"},
    {"ods_number": 7, "objetivo": "Energia Acessível e Limpa"},
    {"ods_number": 8, "objetivo": "Trabalho Decente e Crescimento Econômico"},
    {"ods_number": 9, "objetivo": "Indústria, Inovação e Infraestrutura"},
    {"ods_number": 10, "objetivo": "Redução das Desigualdades"},
    {"ods_number": 11, "objetivo": "Cidades e Comunidades Sustentáveis"},
    {"ods_number": 12, "objetivo": "Consumo e Produção Responsáveis"},
    {"ods_number": 13, "objetivo": "Ação Contra a Mudança Global do Clima"},
    {"ods_number": 14, "objetivo": "Vida na Água"},
    {"ods_number": 15, "objetivo": "Vida Terrestre"},
    {"ods_number": 16, "objetivo": "Paz, Justiça e Instituições Eficazes"},
    {"ods_number": 17, "objetivo": "Parcerias e Meios de Implementação"},
]

ODS_METAS = [
    {
        "ods_number": 1,
        "meta_code": "1.1",
        "meta_text": "Erradicar a pobreza extrema em todos os lugares",
    },
    {
        "ods_number": 1,
        "meta_code": "1.2",
        "meta_text": "Reduzir pela metade a proporção de pessoas em situação de pobreza",
    },
    {
        "ods_number": 1,
        "meta_code": "1.3",
        "meta_text": "Implementar sistemas de proteção social para todos",
    },
    {
        "ods_number": 1,
        "meta_code": "1.4",
        "meta_text": "Garantir acesso igual a recursos econômicos, serviços básicos e propriedade",
    },
    {
        "ods_number": 1,
        "meta_code": "1.5",
        "meta_text": "Reduzir vulnerabilidade a desastres, choques econômicos e sociais",
    },
    {
        "ods_number": 1,
        "meta_code": "1.a",
        "meta_text": "Mobilizar recursos para erradicação da pobreza",
    },
    {
        "ods_number": 1,
        "meta_code": "1.b",
        "meta_text": "Criar políticas sensíveis às necessidades dos pobres e à igualdade de gênero",
    },
    {
        "ods_number": 2,
        "meta_code": "2.1",
        "meta_text": "Acabar com a fome e garantir acesso a alimentos seguros, nutritivos e suficientes",
    },
    {
        "ods_number": 2,
        "meta_code": "2.2",
        "meta_text": "Acabar com todas as formas de má nutrição",
    },
    {
        "ods_number": 2,
        "meta_code": "2.3",
        "meta_text": "Dobrar a produtividade e renda dos pequenos produtores agrícolas",
    },
    {
        "ods_number": 2,
        "meta_code": "2.4",
        "meta_text": "Garantir sistemas sustentáveis de produção de alimentos e práticas resilientes",
    },
    {
        "ods_number": 2,
        "meta_code": "2.5",
        "meta_text": "Manter a diversidade genética de sementes, plantas e animais",
    },
    {
        "ods_number": 2,
        "meta_code": "2.a",
        "meta_text": "Aumentar investimento em infraestrutura rural e pesquisa agrícola",
    },
    {
        "ods_number": 2,
        "meta_code": "2.b",
        "meta_text": "Corrigir restrições e distorções comerciais agrícolas",
    },
    {
        "ods_number": 2,
        "meta_code": "2.c",
        "meta_text": "Garantir o funcionamento estável dos mercados de alimentos",
    },
    {
        "ods_number": 3,
        "meta_code": "3.1",
        "meta_text": "Reduzir a taxa de mortalidade materna global",
    },
    {
        "ods_number": 3,
        "meta_code": "3.2",
        "meta_text": "Acabar com mortes evitáveis de recém-nascidos e crianças menores de 5 anos",
    },
    {
        "ods_number": 3,
        "meta_code": "3.3",
        "meta_text": "Acabar com epidemias de AIDS, tuberculose, malária e doenças tropicais negligenciadas",
    },
    {
        "ods_number": 3,
        "meta_code": "3.4",
        "meta_text": "Reduzir mortalidade prematura por doenças não transmissíveis",
    },
    {
        "ods_number": 3,
        "meta_code": "3.5",
        "meta_text": "Fortalecer prevenção e tratamento do abuso de substâncias",
    },
    {
        "ods_number": 3,
        "meta_code": "3.6",
        "meta_text": "Reduzir pela metade as mortes por acidentes de trânsito",
    },
    {
        "ods_number": 3,
        "meta_code": "3.7",
        "meta_text": "Garantir acesso universal à saúde sexual e reprodutiva",
    },
    {
        "ods_number": 3,
        "meta_code": "3.8",
        "meta_text": "Alcançar cobertura universal de saúde",
    },
    {
        "ods_number": 3,
        "meta_code": "3.9",
        "meta_text": "Reduzir mortes e doenças causadas por poluição e contaminação",
    },
    {
        "ods_number": 3,
        "meta_code": "3.a",
        "meta_text": "Fortalecer implementação da Convenção-Quadro para Controle do Tabaco",
    },
    {
        "ods_number": 3,
        "meta_code": "3.b",
        "meta_text": "Apoiar pesquisa e acesso a vacinas e medicamentos essenciais",
    },
    {
        "ods_number": 3,
        "meta_code": "3.c",
        "meta_text": "Aumentar financiamento e capacitação de profissionais de saúde",
    },
    {
        "ods_number": 3,
        "meta_code": "3.d",
        "meta_text": "Reforçar capacidade para gestão de riscos à saúde",
    },
    {
        "ods_number": 4,
        "meta_code": "4.1",
        "meta_text": "Garantir educação primária e secundária gratuita, equitativa e de qualidade",
    },
    {
        "ods_number": 4,
        "meta_code": "4.2",
        "meta_text": "Acesso a desenvolvimento infantil e educação pré-escolar de qualidade",
    },
    {
        "ods_number": 4,
        "meta_code": "4.3",
        "meta_text": "Igualdade de acesso ao ensino técnico, profissional e superior",
    },
    {
        "ods_number": 4,
        "meta_code": "4.4",
        "meta_text": "Aumentar número de jovens e adultos com habilidades para emprego",
    },
    {
        "ods_number": 4,
        "meta_code": "4.5",
        "meta_text": "Eliminar disparidades de gênero e vulnerabilidade na educação",
    },
    {
        "ods_number": 4,
        "meta_code": "4.6",
        "meta_text": "Assegurar alfabetização e numeramento para todos os adultos",
    },
    {
        "ods_number": 4,
        "meta_code": "4.7",
        "meta_text": "Garantir que todos adquiram conhecimentos para o desenvolvimento sustentável",
    },
    {
        "ods_number": 4,
        "meta_code": "4.a",
        "meta_text": "Construir instalações educacionais seguras, inclusivas e eficazes",
    },
    {
        "ods_number": 4,
        "meta_code": "4.b",
        "meta_text": "Expandir bolsas de estudo para países em desenvolvimento",
    },
    {
        "ods_number": 4,
        "meta_code": "4.c",
        "meta_text": "Aumentar o número de professores qualificados",
    },
    {
        "ods_number": 5,
        "meta_code": "5.1",
        "meta_text": "Acabar com todas as formas de discriminação contra mulheres e meninas",
    },
    {
        "ods_number": 5,
        "meta_code": "5.2",
        "meta_text": "Eliminar todas as formas de violência contra mulheres e meninas",
    },
    {
        "ods_number": 5,
        "meta_code": "5.3",
        "meta_text": "Eliminar práticas nocivas como casamento infantil e mutilação genital feminina",
    },
    {
        "ods_number": 5,
        "meta_code": "5.4",
        "meta_text": "Reconhecer e valorizar o trabalho de cuidado não remunerado",
    },
    {
        "ods_number": 5,
        "meta_code": "5.5",
        "meta_text": "Garantir plena participação e igualdade de oportunidades de liderança",
    },
    {
        "ods_number": 5,
        "meta_code": "5.6",
        "meta_text": "Garantir acesso universal à saúde sexual e reprodutiva",
    },
    {
        "ods_number": 5,
        "meta_code": "5.a",
        "meta_text": "Realizar reformas para garantir igualdade de direitos econômicos",
    },
    {
        "ods_number": 5,
        "meta_code": "5.b",
        "meta_text": "Aumentar o uso de tecnologias que promovam o empoderamento feminino",
    },
    {
        "ods_number": 5,
        "meta_code": "5.c",
        "meta_text": "Adotar políticas e legislação para promover igualdade de gênero",
    },
    {
        "ods_number": 6,
        "meta_code": "6.1",
        "meta_text": "Atingir o acesso universal e equitativo à água potável segura e acessível para todos",
    },
    {
        "ods_number": 6,
        "meta_code": "6.2",
        "meta_text": "Atingir acesso a saneamento e higiene adequados e equitativos para todos",
    },
    {
        "ods_number": 6,
        "meta_code": "6.3",
        "meta_text": "Melhorar a qualidade da água, reduzindo poluição e despejo de resíduos",
    },
    {
        "ods_number": 6,
        "meta_code": "6.4",
        "meta_text": "Aumentar a eficiência no uso da água e assegurar suprimento sustentável",
    },
    {
        "ods_number": 6,
        "meta_code": "6.5",
        "meta_text": "Implementar gestão integrada dos recursos hídricos em todos os níveis",
    },
    {
        "ods_number": 6,
        "meta_code": "6.6",
        "meta_text": "Proteger e restaurar ecossistemas relacionados com a água",
    },
    {
        "ods_number": 6,
        "meta_code": "6.a",
        "meta_text": "Ampliar cooperação internacional para infraestrutura e tecnologias de saneamento",
    },
    {
        "ods_number": 6,
        "meta_code": "6.b",
        "meta_text": "Apoiar e fortalecer a participação das comunidades locais na gestão da água",
    },
    {
        "ods_number": 7,
        "meta_code": "7.1",
        "meta_text": "Garantir acesso universal, confiável e moderno a serviços de energia",
    },
    {
        "ods_number": 7,
        "meta_code": "7.2",
        "meta_text": "Aumentar substancialmente a participação de energias renováveis",
    },
    {
        "ods_number": 7,
        "meta_code": "7.3",
        "meta_text": "Dobrar a taxa global de melhoria da eficiência energética",
    },
    {
        "ods_number": 7,
        "meta_code": "7.a",
        "meta_text": "Reforçar cooperação internacional para pesquisa e tecnologias de energia limpa",
    },
    {
        "ods_number": 7,
        "meta_code": "7.b",
        "meta_text": "Expandir infraestrutura e modernizar tecnologia energética sustentável",
    },
    {
        "ods_number": 8,
        "meta_code": "8.1",
        "meta_text": "Sustentar crescimento econômico per capita de acordo com as circunstâncias nacionais",
    },
    {
        "ods_number": 8,
        "meta_code": "8.2",
        "meta_text": "Atingir níveis mais altos de produtividade econômica por meio da diversificação e inovação",
    },
    {
        "ods_number": 8,
        "meta_code": "8.3",
        "meta_text": "Promover políticas orientadas ao desenvolvimento produtivo e trabalho decente",
    },
    {
        "ods_number": 8,
        "meta_code": "8.4",
        "meta_text": "Melhorar progressivamente a eficiência no uso de recursos globais",
    },
    {
        "ods_number": 8,
        "meta_code": "8.5",
        "meta_text": "Alcançar emprego pleno e produtivo para todas as pessoas",
    },
    {
        "ods_number": 8,
        "meta_code": "8.6",
        "meta_text": "Reduzir substancialmente a proporção de jovens sem emprego ou treinamento",
    },
    {
        "ods_number": 8,
        "meta_code": "8.7",
        "meta_text": "Erradicar trabalho forçado e formas modernas de escravidão",
    },
    {
        "ods_number": 8,
        "meta_code": "8.8",
        "meta_text": "Proteger direitos trabalhistas e promover ambientes seguros",
    },
    {
        "ods_number": 8,
        "meta_code": "8.9",
        "meta_text": "Promover turismo sustentável que gere empregos e promova cultura local",
    },
    {
        "ods_number": 8,
        "meta_code": "8.10",
        "meta_text": "Fortalecer instituições financeiras e acesso a serviços bancários",
    },
    {
        "ods_number": 8,
        "meta_code": "8.a",
        "meta_text": "Aumentar apoio a países em desenvolvimento para programas de emprego",
    },
    {
        "ods_number": 8,
        "meta_code": "8.b",
        "meta_text": "Desenvolver estratégia global de emprego juvenil",
    },
    {
        "ods_number": 9,
        "meta_code": "9.1",
        "meta_text": "Desenvolver infraestrutura de qualidade, confiável, sustentável e resiliente",
    },
    {
        "ods_number": 9,
        "meta_code": "9.2",
        "meta_text": "Promover industrialização inclusiva e sustentável",
    },
    {
        "ods_number": 9,
        "meta_code": "9.3",
        "meta_text": "Aumentar acesso de pequenas indústrias a serviços financeiros e mercados",
    },
    {
        "ods_number": 9,
        "meta_code": "9.4",
        "meta_text": "Modernizar infraestrutura e indústrias para sustentabilidade",
    },
    {
        "ods_number": 9,
        "meta_code": "9.5",
        "meta_text": "Aumentar pesquisa científica e capacidade tecnológica",
    },
    {
        "ods_number": 9,
        "meta_code": "9.a",
        "meta_text": "Facilitar infraestrutura sustentável nos países em desenvolvimento",
    },
    {
        "ods_number": 9,
        "meta_code": "9.b",
        "meta_text": "Apoiar políticas de industrialização inclusiva em países em desenvolvimento",
    },
    {
        "ods_number": 9,
        "meta_code": "9.c",
        "meta_text": "Aumentar acesso às tecnologias da informação e comunicação",
    },
    {
        "ods_number": 10,
        "meta_code": "10.1",
        "meta_text": "Alcançar crescimento da renda dos 40% mais pobres a taxa maior que a média nacional até 2030",
    },
    {
        "ods_number": 10,
        "meta_code": "10.2",
        "meta_text": "Empoderar e promover inclusão social, econômica e política de todos, sem discriminação",
    },
    {
        "ods_number": 10,
        "meta_code": "10.3",
        "meta_text": "Garantir igualdade de oportunidades e reduzir desigualdades de resultados, eliminando práticas discriminatórias",
    },
    {
        "ods_number": 10,
        "meta_code": "10.4",
        "meta_text": "Adotar políticas fiscais, salariais e de proteção social para aumentar a igualdade",
    },
    {
        "ods_number": 10,
        "meta_code": "10.5",
        "meta_text": "Melhorar regulamentação e monitoramento de mercados e instituições financeiras globais",
    },
    {
        "ods_number": 10,
        "meta_code": "10.6",
        "meta_text": "Assegurar representação mais forte dos países em desenvolvimento em decisões econômicas e financeiras globais",
    },
    {
        "ods_number": 10,
        "meta_code": "10.7",
        "meta_text": "Facilitar migração e mobilidade ordenada, segura, regular e responsável das pessoas",
    },
    {
        "ods_number": 10,
        "meta_code": "10.a",
        "meta_text": "Implementar tratamento especial para países em desenvolvimento, conforme acordos da OMC",
    },
    {
        "ods_number": 10,
        "meta_code": "10.b",
        "meta_text": "Incentivar assistência oficial e fluxos financeiros para países mais necessitados",
    },
    {
        "ods_number": 10,
        "meta_code": "10.c",
        "meta_text": "Reduzir custos de remessas de migrantes para menos de 3% até 2030",
    },
    {
        "ods_number": 11,
        "meta_code": "11.1",
        "meta_text": "Assegurar acesso a habitação e serviços básicos adequados, seguros e acessíveis até 2030",
    },
    {
        "ods_number": 11,
        "meta_code": "11.2",
        "meta_text": "Proporcionar transporte seguro, acessível e sustentável, melhorando segurança rodoviária",
    },
    {
        "ods_number": 11,
        "meta_code": "11.3",
        "meta_text": "Aumentar urbanização inclusiva e sustentável e capacidade de planejamento participativo",
    },
    {
        "ods_number": 11,
        "meta_code": "11.4",
        "meta_text": "Proteger e salvaguardar patrimônio cultural e natural",
    },
    {
        "ods_number": 11,
        "meta_code": "11.5",
        "meta_text": "Reduzir mortes e perdas econômicas causadas por desastres, protegendo os vulneráveis",
    },
    {
        "ods_number": 11,
        "meta_code": "11.6",
        "meta_text": "Reduzir impacto ambiental negativo per capita das cidades, incluindo qualidade do ar e gestão de resíduos",
    },
    {
        "ods_number": 11,
        "meta_code": "11.7",
        "meta_text": "Garantir acesso universal a espaços públicos seguros e inclusivos",
    },
    {
        "ods_number": 11,
        "meta_code": "11.a",
        "meta_text": "Apoiar relações positivas entre áreas urbanas, periurbanas e rurais",
    },
    {
        "ods_number": 11,
        "meta_code": "11.b",
        "meta_text": "Aumentar cidades que implementam políticas integradas de inclusão, eficiência, clima e resiliência a desastres",
    },
    {
        "ods_number": 11,
        "meta_code": "11.c",
        "meta_text": "Apoiar países menos desenvolvidos na construção de edifícios sustentáveis e resilientes",
    },
    {
        "ods_number": 12,
        "meta_code": "12.1",
        "meta_text": "Implementar Plano Decenal sobre Produção e Consumo Sustentáveis",
    },
    {
        "ods_number": 12,
        "meta_code": "12.2",
        "meta_text": "Alcançar gestão sustentável e uso eficiente de recursos naturais até 2030",
    },
    {
        "ods_number": 12,
        "meta_code": "12.3",
        "meta_text": "Reduzir pela metade desperdício de alimentos per capita e perdas ao longo das cadeias de produção até 2030",
    },
    {
        "ods_number": 12,
        "meta_code": "12.4",
        "meta_text": "Manejar ambientalmente produtos químicos e resíduos, reduzindo impactos negativos",
    },
    {
        "ods_number": 12,
        "meta_code": "12.5",
        "meta_text": "Reduzir substancialmente geração de resíduos via prevenção, reciclagem e reuso até 2030",
    },
    {
        "ods_number": 12,
        "meta_code": "12.6",
        "meta_text": "Incentivar empresas a adotar práticas sustentáveis e integrar informações de sustentabilidade",
    },
    {
        "ods_number": 12,
        "meta_code": "12.7",
        "meta_text": "Promover compras públicas sustentáveis, conforme políticas nacionais",
    },
    {
        "ods_number": 12,
        "meta_code": "12.8",
        "meta_text": "Garantir acesso à informação e conscientização sobre desenvolvimento sustentável até 2030",
    },
    {
        "ods_number": 12,
        "meta_code": "12.a",
        "meta_text": "Apoiar países em desenvolvimento a fortalecer capacidades científicas e tecnológicas",
    },
    {
        "ods_number": 12,
        "meta_code": "12.b",
        "meta_text": "Desenvolver ferramentas para monitorar impactos do turismo sustentável",
    },
    {
        "ods_number": 12,
        "meta_code": "12.c",
        "meta_text": "Racionalizar subsídios ineficientes aos combustíveis fósseis, eliminando distorções de mercado",
    },
    {
        "ods_number": 13,
        "meta_code": "13.1",
        "meta_text": "Reforçar resiliência e capacidade de adaptação a riscos climáticos e desastres",
    },
    {
        "ods_number": 13,
        "meta_code": "13.2",
        "meta_text": "Integrar medidas de mudança climática em políticas e planejamento nacional",
    },
    {
        "ods_number": 13,
        "meta_code": "13.3",
        "meta_text": "Melhorar educação e conscientização sobre mitigação, adaptação e alerta precoce",
    },
    {
        "ods_number": 13,
        "meta_code": "13.a",
        "meta_text": "Mobilizar US$ 100 bilhões anuais para ações de mitigação e operacionalizar Fundo Verde do Clima",
    },
    {
        "ods_number": 13,
        "meta_code": "13.b",
        "meta_text": "Elevar capacidade de planejamento e gestão climática nos países menos desenvolvidos",
    },
    {
        "ods_number": 14,
        "meta_code": "14.1",
        "meta_text": "Reduzir poluição marinha de todos os tipos, incluindo detritos e poluição por nutrientes até 2025",
    },
    {
        "ods_number": 14,
        "meta_code": "14.2",
        "meta_text": "Gerir e proteger ecossistemas marinhos e costeiros de forma sustentável até 2020",
    },
    {
        "ods_number": 14,
        "meta_code": "14.3",
        "meta_text": "Minimizar impactos da acidificação dos oceanos e fortalecer cooperação científica",
    },
    {
        "ods_number": 14,
        "meta_code": "14.4",
        "meta_text": "Regular sobrepesca e pesca ilegal, implementando planos baseados em ciência até 2020",
    },
    {
        "ods_number": 14,
        "meta_code": "14.5",
        "meta_text": "Conservar pelo menos 10% das zonas costeiras e marinhas até 2020",
    },
    {
        "ods_number": 14,
        "meta_code": "14.6",
        "meta_text": "Proibir subsídios à pesca que causam sobrecapacidade e sobrepesca até 2020",
    },
    {
        "ods_number": 14,
        "meta_code": "14.7",
        "meta_text": "Aumentar benefícios econômicos para pequenos Estados insulares e países menos desenvolvidos até 2030",
    },
    {
        "ods_number": 14,
        "meta_code": "14.a",
        "meta_text": "Desenvolver capacidade científica, pesquisa e transferência tecnológica marinha",
    },
    {
        "ods_number": 14,
        "meta_code": "14.b",
        "meta_text": "Garantir acesso de pescadores artesanais a recursos e mercados",
    },
    {
        "ods_number": 14,
        "meta_code": "14.c",
        "meta_text": "Implementar direito internacional do mar, garantindo conservação e uso sustentável dos oceanos",
    },
    {
        "ods_number": 15,
        "meta_code": "15.1",
        "meta_text": "Assegurar conservação e uso sustentável de ecossistemas terrestres e de água doce até 2020",
    },
    {
        "ods_number": 15,
        "meta_code": "15.2",
        "meta_text": "Implementar gestão sustentável de florestas, deter desmatamento e restaurar florestas degradadas até 2020",
    },
    {
        "ods_number": 15,
        "meta_code": "15.3",
        "meta_text": "Combater desertificação, restaurar terras degradadas e alcançar neutralidade da degradação do solo até 2030",
    },
    {
        "ods_number": 15,
        "meta_code": "15.4",
        "meta_text": "Assegurar conservação de ecossistemas de montanha e biodiversidade até 2030",
    },
    {
        "ods_number": 15,
        "meta_code": "15.5",
        "meta_text": "Reduzir degradação de habitats naturais e proteger espécies ameaçadas até 2020",
    },
    {
        "ods_number": 15,
        "meta_code": "15.6",
        "meta_text": "Promover repartição justa de benefícios de recursos genéticos conforme acordos internacionais",
    },
    {
        "ods_number": 15,
        "meta_code": "15.7",
        "meta_text": "Combater caça ilegal e tráfico de espécies da fauna e flora",
    },
    {
        "ods_number": 15,
        "meta_code": "15.8",
        "meta_text": "Prevenir e reduzir impacto de espécies exóticas invasoras até 2020",
    },
    {
        "ods_number": 15,
        "meta_code": "15.9",
        "meta_text": "Integrar valores da biodiversidade e ecossistemas ao planejamento nacional e local até 2020",
    },
    {
        "ods_number": 15,
        "meta_code": "15.a",
        "meta_text": "Mobilizar recursos financeiros para conservação e uso sustentável da biodiversidade",
    },
    {
        "ods_number": 15,
        "meta_code": "15.b",
        "meta_text": "Financiar gestão florestal sustentável e incentivos a países em desenvolvimento",
    },
    {
        "ods_number": 15,
        "meta_code": "15.c",
        "meta_text": "Reforçar apoio global ao combate à caça ilegal e tráfico de espécies",
    },
    {
        "ods_number": 16,
        "meta_code": "16.1",
        "meta_text": "Reduzir todas as formas de violência e taxas de mortalidade relacionadas",
    },
    {
        "ods_number": 16,
        "meta_code": "16.2",
        "meta_text": "Acabar com abuso, exploração, tráfico e violência contra crianças",
    },
    {
        "ods_number": 16,
        "meta_code": "16.3",
        "meta_text": "Promover Estado de Direito e acesso igualitário à justiça",
    },
    {
        "ods_number": 16,
        "meta_code": "16.4",
        "meta_text": "Reduzir fluxos ilegais de armas e dinheiro, recuperar bens roubados e combater crime organizado até 2030",
    },
    {
        "ods_number": 16,
        "meta_code": "16.5",
        "meta_text": "Reduzir corrupção e suborno em todas as formas",
    },
    {
        "ods_number": 16,
        "meta_code": "16.6",
        "meta_text": "Desenvolver instituições eficazes, responsáveis e transparentes",
    },
    {
        "ods_number": 16,
        "meta_code": "16.7",
        "meta_text": "Garantir inclusão, participação e representação na tomada de decisões",
    },
    {
        "ods_number": 16,
        "meta_code": "16.8",
        "meta_text": "Ampliar participação de países em desenvolvimento em governança global",
    },
    {
        "ods_number": 16,
        "meta_code": "16.9",
        "meta_text": "Fornecer identidade legal para todos, incluindo registro de nascimento até 2030",
    },
    {
        "ods_number": 16,
        "meta_code": "16.10",
        "meta_text": "Assegurar acesso público à informação e proteger liberdades fundamentais",
    },
    {
        "ods_number": 16,
        "meta_code": "16.a",
        "meta_text": "Fortalecer instituições nacionais e cooperação internacional para prevenir violência e terrorismo",
    },
    {
        "ods_number": 16,
        "meta_code": "16.b",
        "meta_text": "Promover leis e políticas não discriminatórias para desenvolvimento sustentável",
    },
    {
        "ods_number": 17,
        "meta_code": "17.1",
        "meta_text": "Fortalecer mobilização de recursos internos e apoio internacional para arrecadação",
    },
    {
        "ods_number": 17,
        "meta_code": "17.2",
        "meta_text": "Países desenvolvidos implementarem compromissos em AOD, fornecendo 0,7% da RNB aos países em desenvolvimento",
    },
    {
        "ods_number": 17,
        "meta_code": "17.3",
        "meta_text": "Mobilizar recursos financeiros adicionais a partir de múltiplas fontes",
    },
    {
        "ods_number": 17,
        "meta_code": "17.4",
        "meta_text": "Apoiar sustentabilidade da dívida de longo prazo em países em desenvolvimento",
    },
    {
        "ods_number": 17,
        "meta_code": "17.5",
        "meta_text": "Adotar regimes de promoção de investimentos para países menos desenvolvidos",
    },
    {
        "ods_number": 17,
        "meta_code": "17.6",
        "meta_text": "Melhorar cooperação internacional, ciência, tecnologia e compartilhamento de conhecimento",
    },
    {
        "ods_number": 17,
        "meta_code": "17.7",
        "meta_text": "Promover transferência de tecnologias ambientalmente corretas",
    },
    {
        "ods_number": 17,
        "meta_code": "17.8",
        "meta_text": "Operacionalizar Banco de Tecnologia e mecanismos de apoio à ciência e TIC",
    },
    {
        "ods_number": 17,
        "meta_code": "17.9",
        "meta_text": "Aumentar apoio internacional à capacitação para implementação dos ODS",
    },
    {
        "ods_number": 17,
        "meta_code": "17.10",
        "meta_text": "Promover comércio multilateral baseado em regras, aberto e equitativo",
    },
    {
        "ods_number": 17,
        "meta_code": "17.11",
        "meta_text": "Aumentar exportações de países em desenvolvimento, duplicando participação dos menos desenvolvidos até 2020",
    },
    {
        "ods_number": 17,
        "meta_code": "17.12",
        "meta_text": "Implementar isenção de tarifas e cotas para países menos desenvolvidos",
    },
    {
        "ods_number": 17,
        "meta_code": "17.13",
        "meta_text": "Aumentar estabilidade macroeconômica global via coordenação de políticas",
    },
    {
        "ods_number": 17,
        "meta_code": "17.14",
        "meta_text": "Aumentar coerência de políticas para desenvolvimento sustentável",
    },
    {
        "ods_number": 17,
        "meta_code": "17.15",
        "meta_text": "Respeitar liderança de cada país para políticas de erradicação da pobreza e desenvolvimento sustentável",
    },
    {
        "ods_number": 17,
        "meta_code": "17.16",
        "meta_text": "Reforçar Parceria Global e parcerias multissetoriais para atingir os ODS",
    },
    {
        "ods_number": 17,
        "meta_code": "17.17",
        "meta_text": "Incentivar parcerias públicas, público-privadas e com sociedade civil",
    },
    {
        "ods_number": 17,
        "meta_code": "17.18",
        "meta_text": "Até 2020, reforçar capacitação e disponibilizar dados desagregados confiáveis",
    },
    {
        "ods_number": 17,
        "meta_code": "17.19",
        "meta_text": "Até 2030, desenvolver indicadores de progresso complementares ao PIB e apoiar capacidades estatísticas",
    },
]

CAPTACAO_ROWS = [
    {
        "sessao": "a-empresa-sumario-executivo",
        "tipo_dado": "Dados cadastrais e detalhes organizacionais",
        "gri_code": "GRI 2-1",
        "descricao": "Razão social, nome fantasia, natureza jurídica, ano de fundação, CNPJ e localização da sede",
        "fonte_documental": "Contrato social, cartão CNPJ, apresentação institucional",
        "tipo_evidencia": "Documento oficial, texto institucional",
    },
    {
        "sessao": "a-empresa-sumario-executivo",
        "tipo_dado": "Entidades incluídas no relato e escopo organizacional",
        "gri_code": "GRI 2-2",
        "descricao": "Empresas controladas, unidades operacionais, filiais ou operações contempladas na seção e no relatório",
        "fonte_documental": "Estrutura societária, organograma societário, memorial descritivo",
        "tipo_evidencia": "Tabela, organograma, texto institucional",
    },
    {
        "sessao": "a-empresa-sumario-executivo",
        "tipo_dado": "Principais atividades, produtos, serviços e mercados atendidos",
        "gri_code": "GRI 2-1",
        "descricao": "Descrição objetiva da atuação da organização, portfólio principal e abrangência geográfica/comercial",
        "fonte_documental": "Apresentação institucional, site corporativo, portfólio comercial",
        "tipo_evidencia": "Texto institucional, tabela, brochura",
    },
    {
        "sessao": "a-empresa-sumario-executivo",
        "tipo_dado": "Cadeia de valor e relacionamento com fornecedores e clientes",
        "gri_code": "GRI 2-6",
        "descricao": "Elementos da cadeia de valor, insumos principais, públicos atendidos e elos operacionais relevantes",
        "fonte_documental": "Mapa da cadeia de valor, apresentação institucional, políticas comerciais",
        "tipo_evidencia": "Fluxograma, texto institucional, tabela",
    },
    {
        "sessao": "visao-estrategica-de-sustentabilidade",
        "tipo_dado": "Declaração de missão, visão e valores",
        "gri_code": "GRI 2-22",
        "descricao": "Definições institucionais que orientam a estratégia de sustentabilidade",
        "fonte_documental": "Relatório institucional, site corporativo",
        "tipo_evidencia": "Documento textual",
    },
    {
        "sessao": "visao-estrategica-de-sustentabilidade",
        "tipo_dado": "Política de sustentabilidade (escopo e data)",
        "gri_code": "GRI 2-23",
        "descricao": "Documento que formaliza compromissos e diretrizes ambientais, sociais e econômicas",
        "fonte_documental": "Política institucional",
        "tipo_evidencia": "Documento PDF/Oficial",
    },
    {
        "sessao": "visao-estrategica-de-sustentabilidade",
        "tipo_dado": "Metas de sustentabilidade (curto, médio e longo prazo)",
        "gri_code": "GRI 2-24",
        "descricao": "Objetivos e metas mensuráveis com indicadores de progresso",
        "fonte_documental": "Plano estratégico, relatórios ESG anteriores",
        "tipo_evidencia": "Tabela, gráfico, texto",
    },
    {
        "sessao": "visao-estrategica-de-sustentabilidade",
        "tipo_dado": "Compromissos públicos (ODS, Pacto Global, etc.)",
        "gri_code": "GRI 2-26",
        "descricao": "Aderências formais a pactos e frameworks internacionais",
        "fonte_documental": "Relatórios públicos, site institucional",
        "tipo_evidencia": "Declarações públicas",
    },
    {
        "sessao": "governanca-corporativa",
        "tipo_dado": "Estrutura organizacional e de governança",
        "gri_code": "GRI 2-9",
        "descricao": "Descrição e organograma da estrutura de governança",
        "fonte_documental": "Organograma, estatuto social",
        "tipo_evidencia": "Gráfico, texto",
    },
    {
        "sessao": "governanca-corporativa",
        "tipo_dado": "Políticas de ética e compliance",
        "gri_code": "GRI 2-15",
        "descricao": "Regras de integridade e conduta corporativa",
        "fonte_documental": "Código de ética, política de compliance",
        "tipo_evidencia": "Documento textual",
    },
    {
        "sessao": "governanca-corporativa",
        "tipo_dado": "Canais de denúncia e número de registros",
        "gri_code": "GRI 2-16",
        "descricao": "Ferramentas de comunicação de preocupações críticas",
        "fonte_documental": "Relatório de compliance",
        "tipo_evidencia": "Planilha, relatório textual",
    },
    {
        "sessao": "gestao-ambiental",
        "tipo_dado": "Inventário de emissões GEE (escopos 1, 2, 3)",
        "gri_code": None,
        "descricao": "Emissões diretas e indiretas de gases de efeito estufa",
        "fonte_documental": "Inventário de emissões",
        "tipo_evidencia": "Tabela, relatório técnico",
    },
    {
        "sessao": "gestao-ambiental",
        "tipo_dado": "Consumo total de energia e fontes",
        "gri_code": "GRI 302-1",
        "descricao": "Energia consumida de fontes renováveis e não renováveis",
        "fonte_documental": "Relatório ambiental ou de energia",
        "tipo_evidencia": "Tabela, planilha",
    },
    {
        "sessao": "gestao-ambiental",
        "tipo_dado": "Consumo e reuso de água",
        "gri_code": "GRI 303-3",
        "descricao": "Volume total captado, consumido e reutilizado",
        "fonte_documental": "Relatórios de sustentabilidade ou ambientais",
        "tipo_evidencia": "Tabela, planilha",
    },
    {
        "sessao": "gestao-ambiental",
        "tipo_dado": "Geração e destinação de resíduos",
        "gri_code": None,
        "descricao": "Volumes e métodos de descarte, reciclagem e reuso",
        "fonte_documental": "Planilhas operacionais, relatórios ambientais",
        "tipo_evidencia": "Tabela, gráfico",
    },
    {
        "sessao": "desempenho-social",
        "tipo_dado": "Composição da força de trabalho por gênero e PCDs",
        "gri_code": "GRI 405-1",
        "descricao": "Indicadores de diversidade e inclusão",
        "fonte_documental": "Relatório de RH",
        "tipo_evidencia": "Tabela, planilha",
    },
    {
        "sessao": "desempenho-social",
        "tipo_dado": "Horas médias de treinamento por colaborador",
        "gri_code": "GRI 404-1",
        "descricao": "Indicadores de capacitação e desenvolvimento",
        "fonte_documental": "Relatório de treinamento",
        "tipo_evidencia": "Tabela, gráfico",
    },
    {
        "sessao": "desempenho-social",
        "tipo_dado": "Taxa de acidentes e absenteísmo",
        "gri_code": "GRI 403-9",
        "descricao": "Indicadores de saúde e segurança ocupacional",
        "fonte_documental": "Relatório de SST",
        "tipo_evidencia": "Tabela, planilha",
    },
    {
        "sessao": "desempenho-social",
        "tipo_dado": "Projetos sociais e investimentos comunitários",
        "gri_code": "GRI 413-1",
        "descricao": "Atividades de engajamento e investimento social privado",
        "fonte_documental": "Relatório social",
        "tipo_evidencia": "Texto, tabela",
    },
    {
        "sessao": "gestao-de-desempenho-economico",
        "tipo_dado": "Receita, lucro e distribuição de valor adicionado",
        "gri_code": "GRI 201-1",
        "descricao": "Indicadores financeiros e econômicos",
        "fonte_documental": "Relatórios financeiros e contábeis",
        "tipo_evidencia": "Tabela, planilha",
    },
    {
        "sessao": "gestao-de-desempenho-economico",
        "tipo_dado": "Investimentos em sustentabilidade e inovação",
        "gri_code": "GRI 203-1",
        "descricao": "Recursos aplicados em projetos de impacto positivo",
        "fonte_documental": "Planos de investimento",
        "tipo_evidencia": "Tabela, texto",
    },
    {
        "sessao": "gestao-de-desempenho-economico",
        "tipo_dado": "Política de compras sustentáveis",
        "gri_code": "GRI 204-1",
        "descricao": "Critérios ESG para fornecedores",
        "fonte_documental": "Política de compras",
        "tipo_evidencia": "Documento textual",
    },
    {
        "sessao": "relacionamento-com-stakeholders",
        "tipo_dado": "Matriz de stakeholders",
        "gri_code": "GRI 2-29",
        "descricao": "Mapeamento e priorização de partes interessadas",
        "fonte_documental": "Relatório de engajamento",
        "tipo_evidencia": "Tabela, gráfico",
    },
    {
        "sessao": "relacionamento-com-stakeholders",
        "tipo_dado": "Registros de reuniões e feedbacks",
        "gri_code": "GRI 413-1",
        "descricao": "Documentação de interações e respostas",
        "fonte_documental": "Atas, relatórios de reuniões",
        "tipo_evidencia": "Texto, planilha",
    },
    {
        "sessao": "inovacao-e-desenvolvimento-tecnologico",
        "tipo_dado": "Projetos e investimentos em P&D",
        "gri_code": "GRI 203-1",
        "descricao": "Iniciativas e recursos aplicados em inovação",
        "fonte_documental": "Relatório de inovação",
        "tipo_evidencia": "Tabela, texto",
    },
    {
        "sessao": "inovacao-e-desenvolvimento-tecnologico",
        "tipo_dado": "Tecnologias sustentáveis implementadas",
        "gri_code": "GRI 302-4",
        "descricao": "Inovações voltadas à eficiência e sustentabilidade",
        "fonte_documental": "Relatórios técnicos",
        "tipo_evidencia": "Texto, tabela",
    },
    {
        "sessao": "relatorios-e-normas",
        "tipo_dado": "Histórico de relatórios ESG anteriores",
        "gri_code": "GRI 2-3",
        "descricao": "Anos e versões anteriores de relatórios de sustentabilidade",
        "fonte_documental": "Arquivo institucional",
        "tipo_evidencia": "Documento PDF",
    },
    {
        "sessao": "relatorios-e-normas",
        "tipo_dado": "Matriz de materialidade",
        "gri_code": "GRI 2-14",
        "descricao": "Temas materiais e sua priorização",
        "fonte_documental": "Relatórios de materialidade",
        "tipo_evidencia": "Tabela, gráfico",
    },
    {
        "sessao": "comunicacao-e-transparencia",
        "tipo_dado": "Plano e canais de comunicação ESG",
        "gri_code": "GRI 417-3",
        "descricao": "Estratégia e meios de divulgação pública de práticas ESG",
        "fonte_documental": "Plano de comunicação",
        "tipo_evidencia": "Texto, documento",
    },
    {
        "sessao": "comunicacao-e-transparencia",
        "tipo_dado": "Relatórios e campanhas publicadas",
        "gri_code": "GRI 2-28",
        "descricao": "Evidências de divulgação pública",
        "fonte_documental": "Relatórios de comunicação",
        "tipo_evidencia": "Imagem, link, PDF",
    },
    {
        "sessao": "auditorias-e-avaliacoes",
        "tipo_dado": "Relatórios de auditorias internas e externas",
        "gri_code": "GRI 2-27",
        "descricao": "Resultados de verificação e conformidade ESG",
        "fonte_documental": "Relatórios de auditoria",
        "tipo_evidencia": "Documento PDF",
    },
    {
        "sessao": "auditorias-e-avaliacoes",
        "tipo_dado": "Certificações e selos ambientais",
        "gri_code": None,
        "descricao": "Comprovação de conformidade ambiental",
        "fonte_documental": "Certificados ISO, selos",
        "tipo_evidencia": "Imagem, documento",
    },
]

INDICATOR_TEMPLATES = [
    {
        "tema": "Clima e Energia",
        "indicador": "Consumo total de energia",
        "unidade": "kWh/ano",
    },
    {
        "tema": "Clima e Energia",
        "indicador": "Intensidade energética",
        "unidade": "kWh/unidade produzida",
    },
    {
        "tema": "Clima e Energia",
        "indicador": "Emissões GEE – Scope 1",
        "unidade": "tCO₂e",
    },
    {
        "tema": "Clima e Energia",
        "indicador": "Emissões GEE – Scope 2",
        "unidade": "tCO₂e",
    },
    {
        "tema": "Clima e Energia",
        "indicador": "Emissões GEE – Scope 3",
        "unidade": "tCO₂e",
    },
    {
        "tema": "Clima e Energia",
        "indicador": "Metas de redução de GEE",
        "unidade": "% redução até 20XX",
    },
    {"tema": "Água", "indicador": "Consumo total de água", "unidade": "m³/ano"},
    {
        "tema": "Água",
        "indicador": "Intensidade hídrica",
        "unidade": "m³/unidade produzida",
    },
    {"tema": "Água", "indicador": "Percentual de água reutilizada", "unidade": "%"},
    {"tema": "Resíduos", "indicador": "Total de resíduos gerados", "unidade": "t/ano"},
    {"tema": "Resíduos", "indicador": "Percentual reciclado", "unidade": "%"},
    {"tema": "Resíduos", "indicador": "Percentual destinado ao reuso", "unidade": "%"},
    {
        "tema": "Resíduos",
        "indicador": "Percentual destinado ao aterro/incineração",
        "unidade": "%",
    },
    {
        "tema": "Saúde e Segurança do Trabalho",
        "indicador": "Taxa de frequência de acidentes (LTIFR)",
        "unidade": "índice",
    },
    {
        "tema": "Saúde e Segurança do Trabalho",
        "indicador": "Dias perdidos por acidentes",
        "unidade": "dias",
    },
    {
        "tema": "Saúde e Segurança do Trabalho",
        "indicador": "Número de acidentes com afastamento",
        "unidade": "unidades",
    },
    {
        "tema": "Capital Humano",
        "indicador": "Média de horas de treinamento por colaborador",
        "unidade": "h/ano",
    },
    {
        "tema": "Capital Humano",
        "indicador": "Percentual de diversidade – Diretoria",
        "unidade": "%",
    },
    {
        "tema": "Capital Humano",
        "indicador": "Percentual de diversidade – Gerência",
        "unidade": "%",
    },
    {
        "tema": "Capital Humano",
        "indicador": "Percentual de diversidade – Operacional",
        "unidade": "%",
    },
    {
        "tema": "Governança / Ética",
        "indicador": "Número de denúncias recebidas",
        "unidade": "unidades",
    },
    {
        "tema": "Governança / Ética",
        "indicador": "Número de denúncias resolvidas",
        "unidade": "unidades",
    },
    {
        "tema": "Desempenho Econômico",
        "indicador": "Investimentos em projetos sustentáveis (CAPEX/OPEX)",
        "unidade": "R$ milhões/ano",
    },
    {
        "tema": "Desempenho Econômico",
        "indicador": "Receita proveniente de produtos/serviços sustentáveis",
        "unidade": "R$ milhões/ano",
    },
    {
        "tema": "Desempenho Econômico",
        "indicador": "Valor econômico gerado e distribuído",
        "unidade": "R$ milhões/ano",
    },
]


_GRI_TABLE = sa.table(
    "gri_standards",
    sa.column("code", sa.String),
    sa.column("family", sa.String),
    sa.column("standard_text", sa.Text),
)

_ODS_GOALS_TABLE = sa.table(
    "ods_goals",
    sa.column("ods_number", sa.Integer),
    sa.column("objetivo", sa.String),
)

_ODS_METAS_TABLE = sa.table(
    "ods_metas",
    sa.column("ods_id", sa.Integer),
    sa.column("meta_code", sa.String),
    sa.column("meta_text", sa.Text),
)

_CAPTACAO_TABLE = sa.table(
    "captacao_matriz",
    sa.column("sessao", sa.String),
    sa.column("tipo_dado", sa.String),
    sa.column("gri_code", sa.String),
    sa.column("descricao", sa.Text),
    sa.column("fonte_documental", sa.String),
    sa.column("tipo_evidencia", sa.String),
)

_INDICATOR_TEMPLATES_TABLE = sa.table(
    "indicator_templates",
    sa.column("tema", sa.String),
    sa.column("indicador", sa.String),
    sa.column("unidade", sa.String),
)


def upgrade() -> None:
    op.bulk_insert(_GRI_TABLE, GRI_STANDARDS)
    op.bulk_insert(_ODS_GOALS_TABLE, ODS_GOALS)

    bind = op.get_bind()
    result = bind.execute(sa.text("SELECT id, ods_number FROM ods_goals"))
    ods_id_by_number = {row.ods_number: row.id for row in result}

    metas_with_fk = [
        {
            "ods_id": ods_id_by_number[row["ods_number"]],
            "meta_code": row["meta_code"],
            "meta_text": row["meta_text"],
        }
        for row in ODS_METAS
    ]
    op.bulk_insert(_ODS_METAS_TABLE, metas_with_fk)

    op.bulk_insert(_CAPTACAO_TABLE, CAPTACAO_ROWS)
    op.bulk_insert(_INDICATOR_TEMPLATES_TABLE, INDICATOR_TEMPLATES)


def downgrade() -> None:
    op.execute("DELETE FROM indicator_templates")
    op.execute("DELETE FROM captacao_matriz")
    op.execute("DELETE FROM ods_metas")
    op.execute("DELETE FROM ods_goals")
    op.execute("DELETE FROM gri_standards")
