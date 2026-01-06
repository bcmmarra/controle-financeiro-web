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

SELECT * FROM usuarios;
SELECT * FROM categorias;
SELECT * FROM transacoes;

DELETE FROM categorias;

ALTER TABLE categorias ADD COLUMN usuario_id INT;
ALTER TABLE categorias ADD COLUMN IF NOT EXISTS cor VARCHAR(7) DEFAULT '#3498db';
ALTER TABLE categorias ADD COLUMN IF NOT EXISTS usuario_id INT;


SET SQL_SAFE_UPDATES = 0;

DELETE c1 FROM categorias c1
INNER JOIN categorias c2 
WHERE c1.id > c2.id AND c1.nome = c2.nome;

SET SQL_SAFE_UPDATES = 1;
ALTER TABLE categorias ADD CONSTRAINT uc_nome_categoria UNIQUE (nome);

ALTER TABLE transacoes ADD COLUMN pago BOOLEAN DEFAULT FALSE;
ALTER TABLE transacoes ADD COLUMN metodo_pagamento VARCHAR(50);
ALTER TABLE transacoes ADD COLUMN pago TINYINT(1) DEFAULT 0;


-- 1. Adicionar coluna de status de pagamento
ALTER TABLE transacoes ADD COLUMN pago TINYINT(1) DEFAULT 0;

-- 2. Adicionar coluna para identificar se é parcelado
ALTER TABLE transacoes ADD COLUMN is_parcelado TINYINT(1) DEFAULT 0;

-- 3. Adicionar coluna para o número total de parcelas
ALTER TABLE transacoes ADD COLUMN numero_parcelas INT DEFAULT 1;

-- 4. Adicionar coluna para a parcela atual (ex: 1, 2, 3...)
ALTER TABLE transacoes ADD COLUMN parcela_atual INT DEFAULT 1;

-- 5. Adicionar coluna para vincular as parcelas ao "pai"
ALTER TABLE transacoes ADD COLUMN id_transacao_pai INT NULL;

-- 6. Adicionar coluna para vincular as cores das categorias
ALTER TABLE categorias ADD COLUMN cor VARCHAR(7) DEFAULT '#3498db';

SET FOREIGN_KEY_CHECKS = 0;
TRUNCATE TABLE categorias;
SET FOREIGN_KEY_CHECKS = 1;

ALTER TABLE transacoes ADD COLUMN tipo ENUM('receita', 'despesa') DEFAULT 'despesa';
SELECT tipo, COUNT(*) FROM transacoes GROUP BY tipo;
UPDATE transacoes SET tipo = 'receita' WHERE descricao LIKE '%Salario%';

SET SQL_SAFE_UPDATES = 0;

UPDATE transacoes 
SET tipo = 'receita' 
WHERE descricao LIKE '%Salario%' 
   OR descricao LIKE '%Rendimento%' 
   OR descricao LIKE '%Pix Recebido%';

SET SQL_SAFE_UPDATES = 1;



SET SQL_SAFE_UPDATES = 0;

-- 1. Volta tudo para despesa
UPDATE transacoes SET tipo = 'despesa';

-- 2. Transforma em receita APENAS o que contém palavras-chave de entrada
UPDATE transacoes 
SET tipo = 'receita' 
WHERE descricao LIKE '%Salário%' 
   OR descricao LIKE '%Comissão%' 
   OR descricao LIKE '%Extras%'
   OR valor_total > 0 AND categoria_id = (SELECT id FROM categorias WHERE nome = 'Receitas' LIMIT 1);

SET SQL_SAFE_UPDATES = 1;

ALTER TABLE transacoes ADD COLUMN tipo ENUM('receita', 'despesa') DEFAULT 'despesa';

DESCRIBE transacoes;

ALTER TABLE transacoes MODIFY COLUMN tipo ENUM('despesa', 'receita') DEFAULT 'despesa';
ALTER TABLE transacoes MODIFY COLUMN metodo_pagamento VARCHAR(50);

SET SQL_SAFE_UPDATES = 0;

UPDATE transacoes SET tipo = 'receita' WHERE metodo_pagamento = 'Entrada';
UPDATE transacoes SET tipo = 'despesa' WHERE tipo IS NULL OR tipo = '';

SET SQL_SAFE_UPDATES = 1; -- Reativa a trava por segurança

SELECT id, descricao, valor_total, tipo, metodo_pagamento 
FROM transacoes 
ORDER BY id DESC LIMIT 10;

UPDATE transacoes SET pago = 1 WHERE tipo = 'receita';

SET SQL_SAFE_UPDATES = 0;
-- 1. Garante que a tabela de transações aceite o novo tipo
ALTER TABLE transacoes MODIFY COLUMN tipo ENUM('receita', 'despesa', 'investimento') NOT NULL;
ALTER TABLE transacoes ADD COLUMN metodo VARCHAR(50) DEFAULT 'Dinheiro';
-- 2. Garante que a categoria Poupança esteja marcada como investimento
UPDATE categorias SET tipo = 'investimento' WHERE nome = 'Poupança';
UPDATE transacoes SET metodo = 'Dinheiro' WHERE metodo IS NULL OR metodo = 'None';
SET SQL_SAFE_UPDATES = 1;
-- Força todas as receitas atuais a ficarem como "Pagas"
UPDATE transacoes SET pago = 1 WHERE tipo = 'receita';
SELECT nome, tipo FROM categorias WHERE nome = 'Poupança';
-- Garante que o método de pagamento seja "Entrada" para receitas
UPDATE transacoes SET metodo_pagamento = 'Entrada' WHERE tipo = 'receita';
ALTER TABLE transacoes MODIFY COLUMN tipo ENUM('receita', 'despesa', 'investimento') NOT NULL;
ALTER TABLE categorias MODIFY COLUMN tipo ENUM('receita', 'despesa', 'investimento') NOT NULL;

ALTER TABLE categorias ADD COLUMN tipo ENUM('receita', 'despesa') DEFAULT 'despesa';

INSERT INTO categorias (nome, cor, usuario_id) VALUES ('Investimentos', '#2980b9', 1);