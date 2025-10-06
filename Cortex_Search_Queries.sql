CREATE OR REPLACE STAGE pdf_stage
    DIRECTORY = ( ENABLE = true )
    ENCRYPTION = ( TYPE = 'SNOWFLAKE_SSE' );


CREATE OR REPLACE TEMPORARY TABLE RAW_TEXT AS
SELECT RELATIVE_PATH,TO_VARCHAR(AI_PARSE_DOCUMENT(to_file(file_url), {'mode': 'layout'}):content) AS EXTRACTED_LAYOUT 
    FROM DIRECTORY(@pdf_stage) 
    WHERE RELATIVE_PATH LIKE '%.pdf';

 create or replace TABLE DOCS_CHUNKS_TABLE ( 
    RELATIVE_PATH VARCHAR(16777216), -- Relative path to the PDF file
    CHUNK VARCHAR(16777216), -- Piece of text
    CHUNK_INDEX INTEGER, -- Index for the text
    CATEGORY VARCHAR(16777216) -- Will hold the document category to enable filtering
);   


insert into DOCS_CHUNKS_TABLE (relative_path, chunk, chunk_index)
    select relative_path, 
            c.value::TEXT as chunk,
            c.INDEX::INTEGER as chunk_index
    from 
        raw_text,
        LATERAL FLATTEN( input => SNOWFLAKE.CORTEX.SPLIT_TEXT_RECURSIVE_CHARACTER (
              EXTRACTED_LAYOUT,
              'markdown',
              1512,
              256,
              ['\n\n', '\n', ' ', '']
           )) c;
		   
		   

create or replace CORTEX SEARCH SERVICE DOCS
ON chunk
ATTRIBUTES relative_path, category
warehouse = 'DWHBI_DQM_WH'
TARGET_LAG = '1 hour'
EMBEDDING_MODEL = 'snowflake-arctic-embed-l-v2.0'
as (
    select chunk,
        chunk_index,
        relative_path,
        category
    from docs_chunks_table
);