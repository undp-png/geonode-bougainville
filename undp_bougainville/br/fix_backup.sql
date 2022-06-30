SELECT  'SELECT SETVAL(' ||quote_literal(S.relname)|| ', MAX(' ||quote_ident(C.attname)|| ') ) FROM ' ||quote_ident(T.relname)|| ';'
FROM pg_class AS S, pg_depend AS D, pg_class AS T, pg_attribute AS C
WHERE S.relkind = 'S'
    AND S.oid = D.objid
    AND D.refobjid = T.oid
    AND D.refobjid = C.attrelid
    AND D.refobjsubid = C.attnum
ORDER BY S.relname;
-- psql -Atq -d undp_bougainville_data -c "
select 'DROP SEQUENCE IF EXISTS ' || quote_ident(seq_name) || ' ; CREATE SEQUENCE '  || quote_ident(seq_name) || ' AS integer START WITH 1 INCREMENT BY 1 NO MINVALUE NO MAXVALUE CACHE 1; ALTER TABLE ' || quote_ident(seq_name) || ' OWNER TO undp_bougainville_data; ALTER SEQUENCE ' || quote_literal(seq_name) ||  ' OWNED BY ' || quote_literal(table_name)|| '.fid;ALTER TABLE ONLY ' || quote_literal(table_name) || ' ALTER COLUMN fid SET DEFAULT nextval(' || quote_ident(seq_name) || '::regclass); ALTER TABLE ONLY ' || quote_literal(table_name)  || ' ADD CONSTRAINT ' || quote_literal(key_name) || ' PRIMARY KEY (fid);'
FROM (SELECT t.table_name || '_fid_seq' seq_name, t.table_name || '_key' key_name, t.table_name, t.table_schema  from information_schema.tables t
inner join information_schema.columns c on c.table_name = t.table_name
                                and c.table_schema = t.table_schema
where c.column_name = 'fid'
      and t.table_schema not in ('information_schema', 'pg_catalog')
      and t.table_type = 'BASE TABLE'
order by t.table_schema) a;" -o /tmp/reset_fid_seq.sql

-- sed -i s/\'/\"/g /tmp/reset_fid_seq.sql
-- psql -d undp_bougainville_data -f /tmp/reset_fid_seq.sql

SELECT 'CREATE INDEX ' || quote_ident(index_name) || ' ON ' || quote_ident(table_name) || ' USING gist (' || column_name || ');' FROM (
SELECT DISTINCT table_schema, table_name, column_name, table_name || column_name as index_name
  FROM information_schema.columns
 WHERE udt_name = 'geometry'
 ORDER BY table_schema, table_name) a;