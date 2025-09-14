-- Add created_at and updated_at columns to solicitacao_material_formador table

ALTER TABLE solicitacao_material_formador 
ADD COLUMN created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;

ALTER TABLE solicitacao_material_formador 
ADD COLUMN updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;

-- Update existing records to have created_at equal to data_solicitacao
UPDATE solicitacao_material_formador 
SET created_at = data_solicitacao 
WHERE created_at IS NULL;

-- Update existing records to have updated_at equal to data_solicitacao or current timestamp
UPDATE solicitacao_material_formador 
SET updated_at = COALESCE(data_resposta, data_solicitacao, CURRENT_TIMESTAMP) 
WHERE updated_at IS NULL;