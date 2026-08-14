export interface DatabaseColumn {
  name: string;
  data_type: string;
  database_type: string;
  nullable: boolean;
  default: string | null;
  primary_key: boolean;
  position: number;
}

export interface DatabaseIndex {
  name: string;
  definition: string;
}

export interface DatabaseTable {
  id: string;
  schema: string;
  name: string;
  estimated_rows: number;
  total_bytes: number;
  columns: DatabaseColumn[];
  indexes: DatabaseIndex[];
}

export interface DatabaseRelation {
  name: string;
  source_table: string;
  source_column: string;
  target_table: string;
  target_column: string;
}

export interface DatabaseSchema {
  database: string;
  postgres_version: string;
  tables: DatabaseTable[];
  relations: DatabaseRelation[];
}
