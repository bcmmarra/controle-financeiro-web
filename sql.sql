-- 1. Cria o banco de dados
CREATE DATABASE IF NOT EXISTS controle_financeiro;
USE controle_financeiro;

-- 2. Tabela de Usuários
CREATE TABLE  IF NOT EXISTS usuarios (
    id INT AUTO_INCREMENT PRIMARY KEY,
    nome VARCHAR(100) NOT NULL,
    email VARCHAR(100) NOT NULL UNIQUE,
    senha VARCHAR(255) NOT NULL
);

-- 3. Tabela de Categorias
CREATE TABLE IF NOT EXISTS categorias (
    id INT AUTO_INCREMENT PRIMARY KEY,
    nome VARCHAR(50) NOT NULL
);

-- 4. Tabela de Transações
CREATE TABLE IF NOT EXISTS transacoes (
    id INT AUTO_INCREMENT PRIMARY KEY,
    usuario_id INT NOT NULL,
    categoria_id INT NOT NULL,
    valor_total DECIMAL(10, 2) NOT NULL,
    descricao VARCHAR(255),
    data_transacao DATE NOT NULL,
    metodo_pagamento ENUM('Dinheiro', 'Pix', 'Cartão de Crédito', 'Cartão de Débito') NOT NULL,
    tipo ENUM('receita', 'despesa') NOT NULL,
    is_parcelado BOOLEAN DEFAULT FALSE,
    numero_parcelas INT DEFAULT 1,
    parcela_atual INT DEFAULT 1,
    id_transacao_pai INT NULL, -- Para agrupar parcelas de uma mesma compra
    FOREIGN KEY (usuario_id) REFERENCES usuarios(id),
    FOREIGN KEY (categoria_id) REFERENCES categorias(id)
);

-- 5. Inserindo algumas categorias iniciais para teste
INSERT IGNORE INTO categorias (nome)
VALUES 	('Alimentação'),
		('Transporte'),
		('Lazer'),
        ('Salário'),
        ('Aluguel');

-- Criando o primeiro usuário para teste
INSERT IGNORE INTO usuarios (nome, email, senha) 
VALUES ('Usuario Teste', 'bruno@email.com', '123456');

INSERT IGNORE INTO usuarios (id, nome, email, senha) 
VALUES (1, 'Bruno Marra', 'bruno@email.com', '123456');

-- Garante que a categoria ID 1 existe
INSERT IGNORE INTO categorias (id, nome) 
VALUES (1, 'Geral');

UPDATE categorias SET nome = TRIM(nome);
ALTER TABLE categorias ADD CONSTRAINT uc_nome_categoria UNIQUE (nome);

-- SET SQL_SAFE_UPDATES = 0;
-- UPDATE categorias SET nome = TRIM(nome);
-- SET SQL_SAFE_UPDATES = 1;

SELECT * FROM categorias;
SELECT * FROM transacoes;
SELECT * FROM usuarios;


SET SQL_SAFE_UPDATES = 0;

DELETE c1 FROM categorias c1
INNER JOIN categorias c2 
WHERE c1.id > c2.id AND c1.nome = c2.nome;

SET SQL_SAFE_UPDATES = 1;
ALTER TABLE categorias ADD CONSTRAINT uc_nome_categoria UNIQUE (nome);

ALTER TABLE transacoes ADD COLUMN pago BOOLEAN DEFAULT FALSE;
ALTER TABLE transacoes ADD COLUMN metodo_pagamento VARCHAR(50);