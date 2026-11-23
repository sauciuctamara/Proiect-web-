CREATE DATABASE IF NOT EXISTS crawler_teatru
CHARACTER SET utf8mb4
COLLATE utf8mb4_unicode_ci;

USE crawler_teatru;

-- Crearea tabelei pentru spectacole
CREATE TABLE IF NOT EXISTS spectacole (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    titlu VARCHAR(255) NOT NULL,
    autor VARCHAR(255) NULL,
    regizor VARCHAR(255) NULL,
    descriere TEXT NULL,
    gen VARCHAR(255) NULL,
    limba VARCHAR(255) NULL,
    durata_minute INT UNSIGNED NULL,
    durata_text VARCHAR(255) NULL,
    varsta_recomandata VARCHAR(255) NULL,
    data_premiera DATE NULL,
    distributie_json JSON NULL,
    echipa_json JSON NULL,
    stocare_afis ENUM('file', 'base64') NULL,
    cale_afis VARCHAR(1024) NULL,
    afis_base64 LONGTEXT NULL,
    tip_mime_afis VARCHAR(100) NULL,
    url_sursa_afis VARCHAR(2048) NULL,
    hash_afis CHAR(64) NULL,
    url_sursa VARCHAR(2048) NOT NULL,
    ultima_verificare TIMESTAMP NULL,
    data_creare TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    data_actualizare TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_spectacole_titlu (titlu),
    INDEX idx_spectacole_autor (autor),
    INDEX idx_spectacole_regizor (regizor),
    INDEX idx_spectacole_data_premiera (data_premiera)
) ENGINE = InnoDB DEFAULT CHARACTER SET = utf8mb4 COLLATE = utf8mb4_unicode_ci;

-- Crearea tabelei pentru programul reprezentatiilor
CREATE TABLE IF NOT EXISTS reprezentatii (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    id_spectacol BIGINT UNSIGNED NOT NULL,
    data_ora TIMESTAMP NOT NULL,
    data_ora_sfarsit TIMESTAMP NULL,
    locatie VARCHAR(255) NULL,
    tip_reprezentatie VARCHAR(100) NULL,
    stare VARCHAR(50) NULL,
    observatii TEXT NULL,
    url_sursa VARCHAR(2048) NULL,
    ultima_verificare TIMESTAMP NULL,
    data_creare TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    data_actualizare TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT fk_reprezentatii_spectacol
        FOREIGN KEY (id_spectacol) REFERENCES spectacole (id)
        ON DELETE CASCADE ON UPDATE CASCADE,
    INDEX idx_reprezentatii_id_spectacol (id_spectacol),
    INDEX idx_reprezentatii_data_ora (data_ora),
    INDEX idx_reprezentatii_locatie (locatie),
    INDEX idx_reprezentatii_data_spectacol (id_spectacol, data_ora)
) ENGINE = InnoDB DEFAULT CHARACTER SET = utf8mb4 COLLATE = utf8mb4_unicode_ci;

-- Constrangeri unice pentru a evita duplicatele la rulari multiple prin instructiunea UPSERT
ALTER TABLE spectacole ADD CONSTRAINT uq_spectacole_url UNIQUE (url_sursa(500));
ALTER TABLE reprezentatii ADD CONSTRAINT uq_reprezentatie_timp UNIQUE (id_spectacol, data_ora);


-- !!!!
USE crawler_teatru;
