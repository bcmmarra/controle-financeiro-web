USE controle_financeiro;

-- 1. Tabela de Usuários
CREATE TABLE IF NOT EXISTS usuarios (
    id INT AUTO_INCREMENT PRIMARY KEY,
    nome VARCHAR(100) NOT NULL,
    email VARCHAR(100) NOT NULL UNIQUE,
    senha VARCHAR(255) NOT NULL
);

-- 2. Tabela de Categorias
CREATE TABLE IF NOT EXISTS categorias (
    id INT AUTO_INCREMENT PRIMARY KEY,
    usuario_id INT,
    nome VARCHAR(50) NOT NULL,
    cor VARCHAR(7) DEFAULT '#3498db',
    tipo ENUM('receita', 'despesa', 'investimento') NOT NULL DEFAULT 'despesa',
    is_sistema BOOLEAN DEFAULT FALSE,
    FOREIGN KEY (usuario_id) REFERENCES usuarios(id) ON DELETE CASCADE,
    UNIQUE INDEX idx_nome_usuario (nome, usuario_id)
);

-- 3. Tabela de Transações
CREATE TABLE IF NOT EXISTS transacoes (
    id INT AUTO_INCREMENT PRIMARY KEY,
    usuario_id INT NOT NULL,
    categoria_id INT NOT NULL,
    valor_total DECIMAL(10, 2) NOT NULL,
    descricao VARCHAR(255),
    data_transacao DATE NOT NULL,
    tipo ENUM('receita', 'despesa', 'investimento') NOT NULL,
    metodo VARCHAR(50) DEFAULT 'Dinheiro',
    pago TINYINT(1) DEFAULT 0,
    is_parcelado TINYINT(1) DEFAULT 0,
    numero_parcelas INT DEFAULT 1,
    parcela_atual INT DEFAULT 1,
    id_transacao_pai INT NULL,
    FOREIGN KEY (usuario_id) REFERENCES usuarios(id) ON DELETE CASCADE,
    FOREIGN KEY (categoria_id) REFERENCES categorias(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS metas (
    id INT AUTO_INCREMENT PRIMARY KEY,
    usuario_id INT NOT NULL,
    categoria_id INT NOT NULL,
    valor_limite DECIMAL(10,2) NOT NULL,
    FOREIGN KEY (usuario_id) REFERENCES usuarios(id),
    FOREIGN KEY (categoria_id) REFERENCES categorias(id) ON DELETE CASCADE
);

SET SQL_SAFE_UPDATES = 0;
ALTER TABLE transacoes ADD COLUMN is_recorrente BOOLEAN DEFAULT FALSE;

-- Garante que temos a coluna para identificar o grupo da recorrência
ALTER TABLE transacoes ADD COLUMN id_transacao_pai INT NULL;
INSERT INTO categorias (nome, tipo, usuario_id, cor) VALUES ('Importado (Pendente)', 'despesa', 1, '#6c757d');
ALTER TABLE metas ADD UNIQUE INDEX idx_user_cat (usuario_id, categoria_id);
ALTER TABLE usuarios ADD COLUMN status_ativo TINYINT(1) DEFAULT 0;
ALTER TABLE usuarios ADD COLUMN data_cadastro TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE transacoes ADD COLUMN alerta_enviado TINYINT(1) DEFAULT 0;
DELETE FROM inscricoes_push;
SET SQL_SAFE_UPDATES = 1;


SELECT * FROM usuarios;
SELECT * FROM categorias;
SELECT * FROM metas;
SELECT * FROM inteligencia_regras;
SELECT * FROM inscricoes_push;
SELECT * FROM transacoes;


SELECT SUM(CASE WHEN tipo = 'Receita' THEN valor_total ELSE -valor_total END) as saldo_real 
FROM transacoes 
WHERE usuario_id = 2;

SELECT descricao, valor_total, tipo, data_transacao 
FROM transacoes 
WHERE MONTH(data_transacao) = 1 AND YEAR(data_transacao) = 2026 
AND usuario_id = 2;





CREATE TABLE inteligencia_regras (
    id INT AUTO_INCREMENT PRIMARY KEY,
    usuario_id INT,
    termo VARCHAR(100) NOT NULL,
    categoria_nome VARCHAR(100) NOT NULL,
    FOREIGN KEY (usuario_id) REFERENCES usuarios(id)
);

CREATE TABLE IF NOT EXISTS inscricoes_push (
    id INT AUTO_INCREMENT PRIMARY KEY,
    usuario_id INT NOT NULL,
    nome_dispositivo VARCHAR(100), -- Ex: "iPhone do Bruno"
    subscription_json TEXT NOT NULL, -- O token gerado pelo navegador
    data_criacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (usuario_id) REFERENCES usuarios(id) ON DELETE CASCADE
);

-- 2. Coluna de controle para evitar notificações duplicadas
ALTER TABLE transacoes ADD COLUMN alerta_enviado TINYINT(1) DEFAULT 0;
ALTER TABLE usuarios ADD COLUMN status_ativo TINYINT(1) DEFAULT 0;
ALTER TABLE usuarios ADD COLUMN data_cadastro TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE usuarios ADD COLUMN data_exclusao_programada DATETIME DEFAULT NULL;
ALTER TABLE usuarios ADD COLUMN aviso_exclusao_enviado TINYINT DEFAULT 0;