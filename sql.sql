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
ALTER TABLE transacoes ADD COLUMN id_transacao_pai INT NULL;
-- Garante que temos a coluna para identificar o grupo da recorrência
ALTER TABLE transacoes ADD COLUMN IF NOT EXISTS id_transacao_pai INT NULL;
INSERT INTO categorias (nome, tipo, usuario_id, cor) VALUES ('Importado (Pendente)', 'despesa', 1, '#6c757d');
ALTER TABLE metas ADD UNIQUE INDEX idx_user_cat (usuario_id, categoria_id);
ALTER TABLE usuarios ADD COLUMN status_ativo TINYINT(1) DEFAULT 0;
ALTER TABLE usuarios ADD COLUMN data_cadastro TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
SET SQL_SAFE_UPDATES = 1;

SELECT id, nome, tipo, usuario_id FROM categorias WHERE usuario_id = 2; 
-- (Troque o 1 pelo seu ID de usuário)

SELECT * FROM usuarios;
SELECT * FROM categorias;
SELECT * FROM metas;
SELECT * FROM inteligencia_regras;
SELECT * FROM transacoes;

SHOW COLUMNS FROM transacoes;


CREATE TABLE inteligencia_regras (
    id INT AUTO_INCREMENT PRIMARY KEY,
    usuario_id INT,
    termo VARCHAR(100) NOT NULL,
    categoria_nome VARCHAR(100) NOT NULL,
    FOREIGN KEY (usuario_id) REFERENCES usuarios(id)
);