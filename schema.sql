-- Create the "user" table
CREATE TABLE user(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  matricula INTEGER,
  name TEXT NOT NULL,
  username TEXT NOT NULL,
  password TEXT NOT NULL,
  saldo REAL DEFAULT 0,
  saldo_payroll REAL DEFAULT 0,
  role TEXT NOT NULL,
  serie TEXT, -- 2 EM, 3 EM, 7 EF
  turma TEXT, -- A, B, C
  telefone TEXT,
  email TEXT,
  cpf TEXT
);

-- Create the "produto" table
CREATE TABLE produto(
  id INTEGER PRIMARY KEY,
  nome TEXT NOT NULL, -- pipoca bokus
  descricao TEXT, -- pode ser observações
  valor REAL NOT NULL,
  tipo TEXT, -- salgados, bomboniere, flor de cactus, etc
  quantidade INTEGER
);

-- Create the "venda_produto" table
CREATE TABLE venda_produto(
  id INTEGER PRIMARY KEY,
  data_hora DATETIME DEFAULT CURRENT_TIMESTAMP,
  produto_id INTEGER,
  vendido_por INTEGER,
  vendido_para INTEGER,
  turno TEXT,
  FOREIGN KEY(produto_id) REFERENCES produto(id),
  FOREIGN KEY(vendido_por) REFERENCES user(id),
  FOREIGN KEY(vendido_para) REFERENCES user(id)
);

-- Create the "historico_abastecimento_estoque" table
CREATE TABLE historico_abastecimento_estoque(
  id INTEGER PRIMARY KEY,
  data_hora DATETIME DEFAULT CURRENT_TIMESTAMP,
  descricao TEXT,
  produto_id INTEGER,
  quantidade INTEGER,
  recebido_por INTEGER,
  valor_compra REAL,
  valor_venda REAL,
  FOREIGN KEY(produto_id) REFERENCES produto(id),
  FOREIGN KEY(recebido_por) REFERENCES user(id)
);

-- Create the "controle_pagamento" table
CREATE TABLE controle_pagamento(
  id INTEGER PRIMARY KEY,
  tipo_pagamento TEXT, -- pix, boleto, cartão debito, cartão crédito
  descricao TEXT, -- referente a pagamento de num sei oq
  data_hora DATETIME DEFAULT CURRENT_TIMESTAMP,
  valor REAL,
  liberado_por INTEGER,
  turno TEXT,
  aluno_id INTEGER,
  comprovante TEXT,
  is_payroll BOOLEAN DEFAULT 0, -- caso seja controle de pagamento de uma folha de pagamento
  FOREIGN KEY(aluno_id) REFERENCES user(id),
  FOREIGN KEY(liberado_por) REFERENCES user(id)
);

-- Create relationship between users (user_id funcionário and ohter users)
CREATE TABLE affiliation(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id INTEGER, -- quem é afiliado
  entidade_id INTEGER, -- quem ta acima desse cara
  FOREIGN KEY(user_id) REFERENCES user(id),
  FOREIGN KEY(entidade_id) REFERENCES user(id)
);

-- Create folha de pagamento
CREATE TABLE folha_de_pagamento(
  id INTEGER PRIMARY KEY,
  valor REAL,
  entidade_id INTEGER, -- é o funcionário = pessoa que vai pagar no finaol de tudo
  affiliation_id INTEGER,
  data_hora DATETIME DEFAULT CURRENT_TIMESTAMP,
  liberado_por INTEGER,
  FOREIGN KEY(entidade_id) REFERENCES user(id),
  FOREIGN KEY(liberado_por) REFERENCES user(id),
  FOREIGN KEY(affiliation_id) REFERENCES affiliation(id)
);

-- Cria tabela de histórico de edições de produtos e usuários
CREATE TABLE history_edits (
  id INTEGER PRIMARY KEY,
  data_hora DATETIME DEFAULT CURRENT_TIMESTAMP,
  action_type INTEGER NOT NULL, -- 1 = edita produto, 2 = edita usuário, 3 = adiciona usuário, 4 = remove usuário, 5 = adiciona produto, 6 = remove produto
  action_data JSON NOT NULL,
);