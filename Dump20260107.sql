CREATE DATABASE  IF NOT EXISTS `controle_financeiro` /*!40100 DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci */ /*!80016 DEFAULT ENCRYPTION='N' */;
USE `controle_financeiro`;
-- MySQL dump 10.13  Distrib 8.0.44, for Win64 (x86_64)
--
-- Host: 127.0.0.1    Database: controle_financeiro
-- ------------------------------------------------------
-- Server version	8.0.44

/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!50503 SET NAMES utf8 */;
/*!40103 SET @OLD_TIME_ZONE=@@TIME_ZONE */;
/*!40103 SET TIME_ZONE='+00:00' */;
/*!40014 SET @OLD_UNIQUE_CHECKS=@@UNIQUE_CHECKS, UNIQUE_CHECKS=0 */;
/*!40014 SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0 */;
/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO' */;
/*!40111 SET @OLD_SQL_NOTES=@@SQL_NOTES, SQL_NOTES=0 */;

--
-- Table structure for table `categorias`
--

DROP TABLE IF EXISTS `categorias`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `categorias` (
  `id` int NOT NULL AUTO_INCREMENT,
  `nome` varchar(50) NOT NULL,
  `cor` varchar(7) DEFAULT '#3498db',
  `usuario_id` int DEFAULT NULL,
  `tipo` enum('receita','despesa','investimento') NOT NULL,
  `is_sistema` tinyint(1) DEFAULT '0',
  PRIMARY KEY (`id`),
  UNIQUE KEY `idx_nome_usuario` (`nome`,`usuario_id`)
) ENGINE=InnoDB AUTO_INCREMENT=36 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `categorias`
--

LOCK TABLES `categorias` WRITE;
/*!40000 ALTER TABLE `categorias` DISABLE KEYS */;
INSERT INTO `categorias` VALUES (1,'Salário','#27ae60',1,'receita',1),(2,'Alimentação','#e74c3c',1,'despesa',1),(3,'Moradia','#6a10be',1,'despesa',1),(4,'Transporte','#f1c40f',1,'despesa',1),(5,'Lazer','#1c4938',1,'despesa',1),(6,'Saúde','#9b59b6',1,'despesa',1),(7,'Investimentos','#3498db',1,'investimento',1),(8,'Salário','#27ae60',2,'receita',1),(9,'Alimentação','#e74c3c',2,'despesa',1),(10,'Moradia','#6a10be',2,'despesa',1),(11,'Transporte','#f1c40f',2,'despesa',1),(12,'Lazer','#1c4938',2,'despesa',1),(13,'Saúde','#9b59b6',2,'despesa',1),(14,'Investimentos','#3498db',2,'investimento',1),(15,'Ações','#3498db',1,'investimento',0),(16,'Criptoativos','#3498db',1,'investimento',0),(17,'Renda Fixa (CDB/Tesouro)','#3498db',1,'investimento',0),(18,'Fundos Imobiliários','#3498db',1,'investimento',0),(19,'Importado','#6c757d',2,'despesa',0),(20,'Importado (Pendente)','#6c757d',1,'despesa',0),(22,'Teste','#f1c40f',2,'despesa',0),(24,'Combustível','#ff4757',2,'despesa',0),(25,'Supermercado','#e67e22',2,'despesa',0),(26,'Contas fixas','#9b59b6',2,'despesa',0),(27,'tes','#6c757d',NULL,'receita',0),(28,'tes','#6c757d',2,'receita',0),(29,'tesss','#ffc800',2,'despesa',0),(30,'sdfsf','#e484e6',2,'despesa',0),(31,'','#6c757d',2,'despesa',0),(32,'12346','#6c757d',2,'despesa',0),(33,'aaaaaa','#6c757d',2,'receita',0),(34,'assdff','#6c757d',2,'receita',0),(35,'sffff','#1c89e9',2,'investimento',0);
/*!40000 ALTER TABLE `categorias` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `inteligencia_regras`
--

DROP TABLE IF EXISTS `inteligencia_regras`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `inteligencia_regras` (
  `id` int NOT NULL AUTO_INCREMENT,
  `usuario_id` int DEFAULT NULL,
  `termo` varchar(100) NOT NULL,
  `categoria_nome` varchar(100) NOT NULL,
  PRIMARY KEY (`id`),
  KEY `usuario_id` (`usuario_id`),
  CONSTRAINT `inteligencia_regras_ibfk_1` FOREIGN KEY (`usuario_id`) REFERENCES `usuarios` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=10 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `inteligencia_regras`
--

LOCK TABLES `inteligencia_regras` WRITE;
/*!40000 ALTER TABLE `inteligencia_regras` DISABLE KEYS */;
INSERT INTO `inteligencia_regras` VALUES (1,NULL,'TESTE','tes'),(5,2,'TESTESSAAA',''),(6,2,'123','12346'),(7,2,'ASDDSA','aaaaaa'),(8,2,'ASDDD','assdff'),(9,2,'DFSDFSSDSDF','sffff');
/*!40000 ALTER TABLE `inteligencia_regras` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `metas`
--

DROP TABLE IF EXISTS `metas`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `metas` (
  `id` int NOT NULL AUTO_INCREMENT,
  `usuario_id` int NOT NULL,
  `categoria_id` int NOT NULL,
  `valor_limite` decimal(10,2) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `idx_user_cat` (`usuario_id`,`categoria_id`),
  KEY `categoria_id` (`categoria_id`),
  CONSTRAINT `metas_ibfk_1` FOREIGN KEY (`usuario_id`) REFERENCES `usuarios` (`id`),
  CONSTRAINT `metas_ibfk_2` FOREIGN KEY (`categoria_id`) REFERENCES `categorias` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=26 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `metas`
--

LOCK TABLES `metas` WRITE;
/*!40000 ALTER TABLE `metas` DISABLE KEYS */;
INSERT INTO `metas` VALUES (1,2,22,800.00),(2,2,13,1.00),(3,2,19,5.00),(5,2,9,1.01),(6,2,10,1.00),(7,2,11,1.00),(8,2,12,1.00);
/*!40000 ALTER TABLE `metas` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `transacoes`
--

DROP TABLE IF EXISTS `transacoes`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `transacoes` (
  `id` int NOT NULL AUTO_INCREMENT,
  `usuario_id` int NOT NULL,
  `categoria_id` int NOT NULL,
  `valor_total` decimal(10,2) NOT NULL,
  `descricao` varchar(255) DEFAULT NULL,
  `data_transacao` date NOT NULL,
  `metodo_pagamento` varchar(50) DEFAULT NULL,
  `tipo` enum('receita','despesa','investimento') NOT NULL,
  `is_parcelado` tinyint(1) DEFAULT '0',
  `numero_parcelas` int DEFAULT '1',
  `parcela_atual` int DEFAULT '1',
  `id_transacao_pai` int DEFAULT NULL,
  `pago` tinyint(1) DEFAULT '0',
  `metodo` varchar(50) DEFAULT 'Dinheiro',
  `is_recorrente` tinyint(1) DEFAULT '0',
  PRIMARY KEY (`id`),
  KEY `usuario_id` (`usuario_id`),
  KEY `categoria_id` (`categoria_id`),
  CONSTRAINT `transacoes_ibfk_1` FOREIGN KEY (`usuario_id`) REFERENCES `usuarios` (`id`),
  CONSTRAINT `transacoes_ibfk_2` FOREIGN KEY (`categoria_id`) REFERENCES `categorias` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=698 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `transacoes`
--

LOCK TABLES `transacoes` WRITE;
/*!40000 ALTER TABLE `transacoes` DISABLE KEYS */;
INSERT INTO `transacoes` VALUES (14,2,10,850.00,'Aluguel','2026-02-05',NULL,'despesa',0,1,1,13,1,'Dinheiro',1),(15,2,10,850.00,'Aluguel','2026-03-05',NULL,'despesa',0,1,1,13,0,'Dinheiro',1),(16,2,10,850.00,'Aluguel','2026-04-05',NULL,'despesa',0,1,1,13,0,'Dinheiro',1),(17,2,10,850.00,'Aluguel','2026-05-05',NULL,'despesa',0,1,1,13,0,'Dinheiro',1),(18,2,10,850.00,'Aluguel','2026-06-05',NULL,'despesa',0,1,1,13,0,'Dinheiro',1),(19,2,10,850.00,'Aluguel','2026-07-05',NULL,'despesa',0,1,1,13,0,'Dinheiro',1),(20,2,10,850.00,'Aluguel','2026-08-05',NULL,'despesa',0,1,1,13,0,'Dinheiro',1),(21,2,10,850.00,'Aluguel','2026-09-05',NULL,'despesa',0,1,1,13,0,'Dinheiro',1),(22,2,10,850.00,'Aluguel','2026-10-05',NULL,'despesa',0,1,1,13,0,'Dinheiro',1),(23,2,10,850.00,'Aluguel','2026-11-05',NULL,'despesa',0,1,1,13,0,'Dinheiro',1),(29,2,22,600.00,'Compra Teste','2026-01-05',NULL,'despesa',0,1,1,29,1,'Dinheiro',1),(30,2,9,1000.00,'Compra Teste','2026-02-05',NULL,'despesa',0,1,1,29,1,'Dinheiro',1),(31,2,9,1000.00,'Compra Teste','2026-03-05',NULL,'despesa',0,1,1,29,0,'Dinheiro',1),(32,2,9,1000.00,'Compra Teste','2026-04-05',NULL,'despesa',0,1,1,29,0,'Dinheiro',1),(33,2,9,1000.00,'Compra Teste','2026-05-05',NULL,'despesa',0,1,1,29,0,'Dinheiro',1),(34,2,9,1000.00,'Compra Teste','2026-06-05',NULL,'despesa',0,1,1,29,0,'Dinheiro',1),(35,2,9,1000.00,'Compra Teste','2026-07-05',NULL,'despesa',0,1,1,29,0,'Dinheiro',1),(36,2,9,1000.00,'Compra Teste','2026-08-05',NULL,'despesa',0,1,1,29,0,'Dinheiro',1),(37,2,9,1000.00,'Compra Teste','2026-09-05',NULL,'despesa',0,1,1,29,0,'Dinheiro',1),(38,2,9,1000.00,'Compra Teste','2026-10-05',NULL,'despesa',0,1,1,29,0,'Dinheiro',1),(39,2,9,1000.00,'Compra Teste','2026-11-05',NULL,'despesa',0,1,1,29,0,'Dinheiro',1),(40,2,9,1000.00,'Compra Teste','2026-12-05',NULL,'despesa',0,1,1,29,0,'Dinheiro',1),(41,2,8,850.00,'Aluguel','2026-01-05',NULL,'receita',0,1,1,41,1,'Dinheiro',1),(42,2,8,850.00,'Aluguel','2026-02-05',NULL,'receita',0,1,1,41,1,'Dinheiro',1),(43,2,8,850.00,'Aluguel','2026-03-05',NULL,'receita',0,1,1,41,1,'Dinheiro',1),(44,2,8,850.00,'Aluguel','2026-04-05',NULL,'receita',0,1,1,41,1,'Dinheiro',1),(45,2,8,850.00,'Aluguel','2026-05-05',NULL,'receita',0,1,1,41,1,'Dinheiro',1),(46,2,8,850.00,'Aluguel','2026-06-05',NULL,'receita',0,1,1,41,1,'Dinheiro',1),(47,2,8,850.00,'Aluguel','2026-07-05',NULL,'receita',0,1,1,41,1,'Dinheiro',1),(48,2,8,850.00,'Aluguel','2026-08-05',NULL,'receita',0,1,1,41,1,'Dinheiro',1),(49,2,8,850.00,'Aluguel','2026-09-05',NULL,'receita',0,1,1,41,1,'Dinheiro',1),(50,2,8,850.00,'Aluguel','2026-10-05',NULL,'receita',0,1,1,41,1,'Dinheiro',1),(51,2,14,300.00,'Janeiro','2026-01-05',NULL,'investimento',0,1,1,51,1,'Dinheiro',1),(52,2,14,300.00,'Janeiro','2026-02-05',NULL,'investimento',0,1,1,51,1,'Dinheiro',1),(53,2,14,300.00,'Janeiro','2026-03-05',NULL,'investimento',0,1,1,51,1,'Dinheiro',1),(54,2,14,300.00,'Janeiro','2026-04-05',NULL,'investimento',0,1,1,51,1,'Dinheiro',1),(55,2,14,300.00,'Janeiro','2026-05-05',NULL,'investimento',0,1,1,51,1,'Dinheiro',1),(56,2,14,300.00,'Janeiro','2026-06-05',NULL,'investimento',0,1,1,51,1,'Dinheiro',1),(190,2,19,0.00,'Saldo do dia','0002-11-30',NULL,'despesa',0,1,1,NULL,1,'OFX',0),(547,2,19,0.00,'Saldo Anterior','2025-11-28',NULL,'despesa',0,1,1,NULL,1,'OFX',0),(548,2,19,52.30,'29/11 14:09 JOY CULINARIA ORIENT','2025-12-01',NULL,'despesa',0,1,1,NULL,1,'OFX',0),(549,2,25,42.19,'01/12 19:38 SUP EPA QUARENTA E C','2025-12-01',NULL,'despesa',0,1,1,NULL,1,'OFX',0),(550,2,25,114.19,'29/11 18:06 SUP EPA QUARENTA E C','2025-12-01',NULL,'despesa',0,1,1,NULL,1,'OFX',0),(551,2,19,4.50,'01/12 07:43 DELICIAS DE MINAS','2025-12-01',NULL,'despesa',0,1,1,NULL,1,'OFX',0),(552,2,19,54.80,'30/11 13:14 JOY CULINARIA ORIENT','2025-12-01',NULL,'despesa',0,1,1,NULL,1,'OFX',0),(553,2,19,456.14,'29/11 12:17 NU PAGAMENTOS S/A','2025-12-01',NULL,'despesa',0,1,1,NULL,1,'OFX',0),(555,2,19,2400.00,'01/12 19:08 DEIWIDE SOUZA FONSECA 036','2025-12-01',NULL,'despesa',0,1,1,NULL,1,'OFX',0),(557,2,19,5.50,'02/12 07:21 CAFE METRO','2025-12-02',NULL,'despesa',0,1,1,NULL,1,'OFX',0),(558,2,13,2.39,'02/12 07:58 DROG ARAUJO FILIAL 1','2025-12-02',NULL,'despesa',0,1,1,NULL,1,'OFX',0),(559,2,25,39.50,'02/12 20:48 SUP EPA QUARENTA E C','2025-12-02',NULL,'despesa',0,1,1,NULL,1,'OFX',0),(561,2,19,4.50,'03/12 08:13 DELICIAS DE MINAS','2025-12-03',NULL,'despesa',0,1,1,NULL,1,'OFX',0),(562,2,19,2.50,'03/12 19:40 SergioSilvaMacedo','2025-12-03',NULL,'despesa',0,1,1,NULL,1,'OFX',0),(563,2,19,28.00,'03/12 08:41 DEIWIDE SOUZA FONSECA 036','2025-12-03',NULL,'despesa',0,1,1,NULL,1,'OFX',0),(564,2,19,30.00,'03/12 09:32 DEIWIDE SOUZA FONSECA 036','2025-12-03',NULL,'despesa',0,1,1,NULL,1,'OFX',0),(565,2,19,5.00,'03/12 16:18 DAVI BAIAO MENDES GOULART','2025-12-03',NULL,'despesa',0,1,1,NULL,1,'OFX',0),(567,2,19,13.00,'04/12 20:30 REI DO PASTEL','2025-12-04',NULL,'despesa',0,1,1,NULL,1,'OFX',0),(568,2,24,51.00,'04/12 07:43 POSTO TIC TAC','2025-12-04',NULL,'despesa',0,1,1,NULL,1,'OFX',0),(569,2,19,4.50,'04/12 07:53 DELICIAS DE MINAS','2025-12-04',NULL,'despesa',0,1,1,NULL,1,'OFX',0),(571,2,8,549.00,'05/12 22:28 31401798000107 DENTAL BH B','2025-12-05',NULL,'receita',0,1,1,NULL,1,'OFX',0),(572,2,19,33.25,'05/12 07:11 Superboxsupermerc','2025-12-05',NULL,'despesa',0,1,1,NULL,1,'OFX',0),(574,2,25,2.98,'06/12 18:08 SUP EPA QUARENTA E C','2025-12-08',NULL,'despesa',0,1,1,NULL,1,'OFX',0),(575,2,25,283.42,'07/12 11:05 SUPERMERCADOS BH','2025-12-08',NULL,'despesa',0,1,1,NULL,1,'OFX',0),(576,2,19,4.50,'08/12 07:48 DELICIAS DE MINAS','2025-12-08',NULL,'despesa',0,1,1,NULL,1,'OFX',0),(577,2,19,118.78,'06/12 12:43 MP *BAR24HS','2025-12-08',NULL,'despesa',0,1,1,NULL,1,'OFX',0),(578,2,19,9.50,'06/12 07:38 DELICIAS DE MINAS','2025-12-08',NULL,'despesa',0,1,1,NULL,1,'OFX',0),(579,2,19,8.00,'06/12 07:39 CASA DE SUCOS CONTOR','2025-12-08',NULL,'despesa',0,1,1,NULL,1,'OFX',0),(580,2,19,301.00,'06/12 23:49 MP *EGLUCASVIANA','2025-12-08',NULL,'despesa',0,1,1,NULL,1,'OFX',0),(581,2,25,23.80,'06/12 16:00 SUPERMERCADOS BH','2025-12-08',NULL,'despesa',0,1,1,NULL,1,'OFX',0),(582,2,19,100.00,'06/12 10:41 Fernando Mendes De Carval','2025-12-08',NULL,'despesa',0,1,1,NULL,1,'OFX',0),(583,2,19,17.50,'08/12 15:08 FABRICIO GERALDO ASSIS','2025-12-08',NULL,'despesa',0,1,1,NULL,1,'OFX',0),(585,2,19,4.50,'10/12 07:43 DELICIAS DE MINAS','2025-12-10',NULL,'despesa',0,1,1,NULL,1,'OFX',0),(586,2,11,4.73,'10/12 18:39 UBER DO BRASIL TECNOLOGIA','2025-12-10',NULL,'despesa',0,1,1,NULL,1,'OFX',0),(587,2,19,109.80,'10/12 23:04 SHPP BRASIL INSTITUICAO D','2025-12-10',NULL,'despesa',0,1,1,NULL,1,'OFX',0),(588,2,19,42.97,'10/12 23:18 SHPP BRASIL INSTITUICAO D','2025-12-10',NULL,'despesa',0,1,1,NULL,1,'OFX',0),(590,2,19,8.41,'11/12 07:20 Superboxsupermerc','2025-12-11',NULL,'despesa',0,1,1,NULL,1,'OFX',0),(591,2,19,4.50,'11/12 07:55 DELICIAS DE MINAS','2025-12-11',NULL,'despesa',0,1,1,NULL,1,'OFX',0),(592,2,19,22.76,'11/12 11:45 SHPP BRASIL INSTITUICAO D','2025-12-11',NULL,'despesa',0,1,1,NULL,1,'OFX',0),(593,2,19,29.99,'11/12 11:52 SHPP BRASIL INSTITUICAO D','2025-12-11',NULL,'despesa',0,1,1,NULL,1,'OFX',0),(594,2,19,24.00,'11/12 13:07 Leticia dos Santos Rabelo','2025-12-11',NULL,'despesa',0,1,1,NULL,1,'OFX',0),(595,2,19,100.00,'11/12 19:20 DAVI BAIAO MENDES GOULART','2025-12-11',NULL,'despesa',0,1,1,NULL,1,'OFX',0),(597,2,19,50.00,'12/12 21:05 00009965250685 CAMILA DA S','2025-12-12',NULL,'receita',0,1,1,NULL,1,'OFX',0),(598,2,24,83.64,'12/12 18:12 POSTO OASIS','2025-12-12',NULL,'despesa',0,1,1,NULL,1,'OFX',0),(599,2,19,3.75,'12/12 20:58 SORVETERIA ALMEIDA','2025-12-12',NULL,'despesa',0,1,1,NULL,1,'OFX',0),(600,2,24,50.00,'12/12 21:06 POSTO DA FONTE','2025-12-12',NULL,'despesa',0,1,1,NULL,1,'OFX',0),(601,2,19,30.00,'12/12 12:11 VITORIA','2025-12-12',NULL,'despesa',0,1,1,NULL,1,'OFX',0),(602,2,26,35.79,'12/12 14:52 TIM S A','2025-12-12',NULL,'despesa',0,1,1,NULL,1,'OFX',0),(604,2,19,20.00,'13/12 12:21 00009965250685 CAMILA DA S','2025-12-15',NULL,'receita',0,1,1,NULL,1,'OFX',0),(605,2,19,100.00,'13/12 15:35 00009965250685 CAMILA DA S','2025-12-15',NULL,'receita',0,1,1,NULL,1,'OFX',0),(606,2,19,65.00,'13/12 18:38 09965250685 CAMILA DA SILV','2025-12-15',NULL,'receita',0,1,1,NULL,1,'OFX',0),(607,2,19,150.00,'14/12 11:13 09965250685 Camila da Silv','2025-12-15',NULL,'receita',0,1,1,NULL,1,'OFX',0),(608,2,19,22.97,'13/12 15:56 SergioSilvaMacedo','2025-12-15',NULL,'despesa',0,1,1,NULL,1,'OFX',0),(609,2,25,60.80,'14/12 12:02 SUP EPA QUARENTA E C','2025-12-15',NULL,'despesa',0,1,1,NULL,1,'OFX',0),(610,2,9,64.90,'13/12 18:39 BURGER KING','2025-12-15',NULL,'despesa',0,1,1,NULL,1,'OFX',0),(611,2,25,5.86,'14/12 13:15 SUP EPA QUARENTA E C','2025-12-15',NULL,'despesa',0,1,1,NULL,1,'OFX',0),(612,2,19,13.00,'13/12 20:36 ShoppingContagem','2025-12-15',NULL,'despesa',0,1,1,NULL,1,'OFX',0),(613,2,25,12.57,'13/12 12:44 MINI MERCADO PRIMAVE','2025-12-15',NULL,'despesa',0,1,1,NULL,1,'OFX',0),(614,2,25,10.72,'13/12 12:55 SUP EPA QUARENTA E C','2025-12-15',NULL,'despesa',0,1,1,NULL,1,'OFX',0),(615,2,25,128.46,'14/12 11:14 DMA DISTRIBUIDORA S/A','2025-12-15',NULL,'despesa',0,1,1,NULL,1,'OFX',0),(616,2,19,20.00,'15/12 12:57 CASA DE SUCOS CONTORNO LT','2025-12-15',NULL,'despesa',0,1,1,NULL,1,'OFX',0),(618,2,19,8.00,'16/12 20:30 00015044462675 DAVI BAIAO','2025-12-16',NULL,'receita',0,1,1,NULL,1,'OFX',0),(620,2,19,15.00,'17/12 12:05 09965250685 Camila da Silv','2025-12-17',NULL,'receita',0,1,1,NULL,1,'OFX',0),(621,2,25,7.98,'17/12 08:19 SUPERMERCADO SUPER N','2025-12-17',NULL,'despesa',0,1,1,NULL,1,'OFX',0),(622,2,9,34.50,'17/12 12:07 SUBWAY PRADO','2025-12-17',NULL,'despesa',0,1,1,NULL,1,'OFX',0),(624,2,19,99.65,'18/12 15:15 09965250685 Camila da Silv','2025-12-18',NULL,'receita',0,1,1,NULL,1,'OFX',0),(625,2,19,101.01,'18/12 16:12 BTT TELECOMUNICACOES SA','2025-12-18',NULL,'despesa',0,1,1,NULL,1,'OFX',0),(627,2,8,1629.00,'19/12 17:05 DENTAL BH BRASIL EIRELI','2025-12-19',NULL,'receita',0,1,1,NULL,1,'OFX',0),(628,2,8,695.00,'19/12 17:05 DENTAL BH BRASIL EIRELI','2025-12-19',NULL,'receita',0,1,1,NULL,1,'OFX',0),(629,2,19,322.00,'19/12 17:31 REGIANE BORGES DOS SANTOS','2025-12-19',NULL,'despesa',0,1,1,NULL,1,'OFX',0),(630,2,19,50.00,'19/12 17:33 Bruno Cassio Marra','2025-12-19',NULL,'despesa',0,1,1,NULL,1,'OFX',0),(631,2,19,325.04,'19/12 17:35 FERNANDA MARA BARBOSA DE','2025-12-19',NULL,'despesa',0,1,1,NULL,1,'OFX',0),(632,2,19,425.04,'19/12 17:38 FERNANDA MARA BARBOSA DE','2025-12-19',NULL,'despesa',0,1,1,NULL,1,'OFX',0),(636,2,19,16.00,'22/12 07:57 LANCHE DA HORA','2025-12-22',NULL,'despesa',0,1,1,NULL,1,'OFX',0),(637,2,9,28.40,'22/12 11:56 RESTAURANTE FAMILIA','2025-12-22',NULL,'despesa',0,1,1,NULL,1,'OFX',0),(638,2,19,146.00,'20/12 11:31 ClaudioBragaLemos','2025-12-22',NULL,'despesa',0,1,1,NULL,1,'OFX',0),(639,2,19,30.00,'21/12 Jose Luiz Da Silva Perei 005/005','2025-12-22',NULL,'despesa',0,1,1,NULL,1,'OFX',0),(640,2,9,104.39,'21/12 20:45 IFOOD.COM AGENCIA DE REST','2025-12-22',NULL,'despesa',0,1,1,NULL,1,'OFX',0),(641,2,11,168.30,'22/12 10:16 CMA PROTECAO PATRIMONIAL','2025-12-22',NULL,'despesa',0,1,1,NULL,1,'OFX',0),(642,2,19,290.00,'YAPAY PAGAMENTOS ONLINE LTDA','2025-12-22',NULL,'despesa',0,1,1,NULL,1,'OFX',0),(643,2,19,74.70,'22/12 11:09 SHPP BRASIL INSTITUICAO D','2025-12-22',NULL,'despesa',0,1,1,NULL,1,'OFX',0),(644,2,19,10.00,'22/12 13:06 Henrique Jardim Do Prado','2025-12-22',NULL,'despesa',0,1,1,NULL,1,'OFX',0),(645,2,19,425.00,'22/12 20:40 Camila da Silva Baiao Gou','2025-12-22',NULL,'despesa',0,1,1,NULL,1,'OFX',0),(647,2,19,40.00,'23/12 18:51 IPAMINONDAS FELIPE DE LIM','2025-12-23',NULL,'despesa',0,1,1,NULL,1,'OFX',0),(648,2,19,270.00,'23/12 19:27 EDUARDO RODRIGUES COSTA','2025-12-23',NULL,'despesa',0,1,1,NULL,1,'OFX',0),(650,2,25,22.91,'24/12 09:01 SUP EPA QUARENTA E C','2025-12-24',NULL,'despesa',0,1,1,NULL,1,'OFX',0),(651,2,13,19.99,'24/12 22:04 DROGARIA ARAUJO FL 2','2025-12-24',NULL,'despesa',0,1,1,NULL,1,'OFX',0),(654,2,19,50.00,'25/12 00:17 09340318609 Lucas Borges d','2025-12-26',NULL,'receita',0,1,1,NULL,1,'OFX',0),(655,2,19,10.00,'25/12 00:27 00039209830172 RICHARDSON','2025-12-26',NULL,'receita',0,1,1,NULL,1,'OFX',0),(656,2,19,20.00,'25/12 00:30 00008850301685 RUBIA MARA','2025-12-26',NULL,'receita',0,1,1,NULL,1,'OFX',0),(657,2,19,0.32,'26/12 14:25 02625234180 Bruno Cássio M','2025-12-26',NULL,'receita',0,1,1,NULL,1,'OFX',0),(658,2,9,36.29,'25/12 10:11 PADARIA SAMUEL','2025-12-26',NULL,'despesa',0,1,1,NULL,1,'OFX',0),(659,2,13,45.57,'25/12 16:39 DROGARIA ARAUJO S. A','2025-12-26',NULL,'despesa',0,1,1,NULL,1,'OFX',0),(660,2,19,100.00,'25/12 01:02 JOAO PEDRO BARBOSA MARRA','2025-12-26',NULL,'despesa',0,1,1,NULL,1,'OFX',0),(661,2,19,50.00,'25/12 11:58 Camila da Silva Baiao Gou','2025-12-26',NULL,'despesa',0,1,1,NULL,1,'OFX',0),(662,2,19,170.00,'26/12 09:20 Camila da Silva Baiao Gou','2025-12-26',NULL,'despesa',0,1,1,NULL,1,'OFX',0),(663,2,19,170.00,'26/12 18:25 DAVI BAIAO MENDES GOULART','2025-12-26',NULL,'despesa',0,1,1,NULL,1,'OFX',0),(665,2,25,20.90,'28/12 12:25 SUPERMERCADOS  BH','2025-12-29',NULL,'despesa',0,1,1,NULL,1,'OFX',0),(666,2,13,25.00,'27/12 10:57 DROGARIA CYNTIA','2025-12-29',NULL,'despesa',0,1,1,NULL,1,'OFX',0),(667,2,19,18.00,'28/12 16:34 LUCIMAR DOMINGOS CELESTIN','2025-12-29',NULL,'despesa',0,1,1,NULL,1,'OFX',0),(669,2,19,335.00,'01/12 18:51 HENRI SILVA VILLEFORT COS','2025-12-01',NULL,'despesa',0,1,1,NULL,1,'OFX',0),(670,2,19,3459.12,'Rende Facil','2025-12-01',NULL,'receita',0,1,1,NULL,1,'OFX',0),(671,2,19,47.39,'Rende Facil','2025-12-02',NULL,'receita',0,1,1,NULL,1,'OFX',0),(672,2,19,70.00,'Rende Facil','2025-12-03',NULL,'receita',0,1,1,NULL,1,'OFX',0),(673,2,19,68.50,'Rende Facil','2025-12-04',NULL,'receita',0,1,1,NULL,1,'OFX',0),(674,2,19,515.75,'Rende Facil','2025-12-05',NULL,'despesa',0,1,1,NULL,1,'OFX',0),(675,2,19,869.48,'Rende Facil','2025-12-08',NULL,'receita',0,1,1,NULL,1,'OFX',0),(676,2,19,162.00,'Rende Facil','2025-12-10',NULL,'receita',0,1,1,NULL,1,'OFX',0),(677,2,19,189.66,'Rende Facil','2025-12-11',NULL,'receita',0,1,1,NULL,1,'OFX',0),(678,2,19,153.18,'Rende Facil','2025-12-12',NULL,'receita',0,1,1,NULL,1,'OFX',0),(679,2,19,4.28,'Rende Facil','2025-12-15',NULL,'receita',0,1,1,NULL,1,'OFX',0),(680,2,19,8.00,'Rende Facil','2025-12-16',NULL,'despesa',0,1,1,NULL,1,'OFX',0),(681,2,19,27.48,'Rende Facil','2025-12-17',NULL,'receita',0,1,1,NULL,1,'OFX',0),(682,2,19,1.36,'Rende Facil','2025-12-18',NULL,'receita',0,1,1,NULL,1,'OFX',0),(683,2,19,1201.92,'Rende Facil','2025-12-19',NULL,'despesa',0,1,1,NULL,1,'OFX',0),(684,2,19,1040.00,'22/12 12:06 ARAUJO GUSTAVO AYALA ATMR','2025-12-22',NULL,'receita',0,1,1,NULL,1,'OFX',0),(685,2,19,100.00,'22/12 12:09 ARAUJO GUSTAVO AYALA ATMR','2025-12-22',NULL,'receita',0,1,1,NULL,1,'OFX',0),(686,2,19,442.79,'Rende Facil','2025-12-22',NULL,'receita',0,1,1,NULL,1,'OFX',0),(687,2,19,310.00,'Rende Facil','2025-12-23',NULL,'receita',0,1,1,NULL,1,'OFX',0),(688,2,19,42.90,'Rende Facil','2025-12-24',NULL,'receita',0,1,1,NULL,1,'OFX',0),(689,2,19,150.00,'26/12 12:00 ARAUJO GUSTAVO AYALA ATMR','2025-12-26',NULL,'receita',0,1,1,NULL,1,'OFX',0),(690,2,19,341.54,'Rende Facil','2025-12-26',NULL,'receita',0,1,1,NULL,1,'OFX',0),(691,2,19,63.90,'Rende Facil','2025-12-29',NULL,'receita',0,1,1,NULL,1,'OFX',0),(692,2,22,23.33,'ASD','2026-01-07',NULL,'despesa',0,1,1,NULL,1,'Dinheiro',0),(693,2,22,1.22,'ASDASDDASD','2026-01-07',NULL,'despesa',0,1,1,NULL,1,'Dinheiro',0),(694,2,22,23.33,'0AS','2026-01-07',NULL,'despesa',0,1,1,NULL,1,'Dinheiro',0),(695,2,9,10.00,'Compra Teste1','2026-01-07',NULL,'despesa',0,1,1,NULL,1,'Dinheiro',0),(696,2,9,100.01,'Compra Teste5','2026-01-07',NULL,'despesa',0,1,1,NULL,1,'Dinheiro',0),(697,2,9,1000.11,'Compra Teste2','2026-01-07',NULL,'despesa',0,1,1,NULL,1,'Dinheiro',0);
/*!40000 ALTER TABLE `transacoes` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `usuarios`
--

DROP TABLE IF EXISTS `usuarios`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `usuarios` (
  `id` int NOT NULL AUTO_INCREMENT,
  `nome` varchar(100) NOT NULL,
  `email` varchar(100) NOT NULL,
  `senha` varchar(255) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `email` (`email`)
) ENGINE=InnoDB AUTO_INCREMENT=3 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `usuarios`
--

LOCK TABLES `usuarios` WRITE;
/*!40000 ALTER TABLE `usuarios` DISABLE KEYS */;
INSERT INTO `usuarios` VALUES (1,'BRUNO CASSIO MARRA','teste@email.com','scrypt:32768:8:1$KwPdtgP8FKkKcr0G$84ee7c83a852f470940c29c71116354cb9dfa6ecbfe3c70c94a940ab1c93e70ab1d5d615f97e94c87c9e0f40d8e2d9553e7809490451500f2f3efc3843578796'),(2,'BRUNO CASSIO MARRA','picpay.bcm.marra@gmail.com','scrypt:32768:8:1$FVT5bi7tmUsFuWTr$914ad33c5e4fc0b8a99b2b483aa72e2e2a24d5023ab700d4c054a6e229d6519ba84d4f414bbb886e444153187c0d983491fb6501e5e55159cfc0d66366fce021');
/*!40000 ALTER TABLE `usuarios` ENABLE KEYS */;
UNLOCK TABLES;
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

-- Dump completed on 2026-01-07 13:22:46
