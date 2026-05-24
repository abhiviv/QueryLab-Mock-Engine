import random
from datetime import datetime, timedelta
from typing import Dict, Any, List
from sqlalchemy import create_engine, inspect

def extract_schema_metadata(connection_string: str) -> Dict[str, Any]:
    """
    Reads an arbitrary SQLite or MySQL database on the fly using SQLAlchemy's inspect.
    Returns a structured map of tables, column names, and data types.
    """
    try:
        # Create connection engine (using short timeout for SQLite / local DB connections)
        # Note: connect_args timeout is database-driver specific, so we use standard creation
        engine = create_engine(connection_string)
        
        inspector = inspect(engine)
        tables_metadata = {}
        
        table_names = inspector.get_table_names()
        
        for table_name in table_names:
            columns = inspector.get_columns(table_name)
            pk_constraint = inspector.get_pk_constraint(table_name)
            pk_cols = pk_constraint.get("constrained_columns", [])
            
            table_cols = []
            for col in columns:
                col_name = col["name"]
                # Convert the type object to a readable string representation (e.g. VARCHAR(255), INTEGER)
                col_type = str(col["type"])
                
                table_cols.append({
                    "name": col_name,
                    "type": col_type,
                    "nullable": col.get("nullable", True),
                    "primary_key": col_name in pk_cols
                })
            tables_metadata[table_name] = table_cols
            
        return {
            "success": True,
            "tables": tables_metadata,
            "error": None
        }
    except Exception as e:
        return {
            "success": False,
            "tables": {},
            "error": str(e)
        }

def generate_mock_records(columns: List[Dict[str, Any]], count: int) -> List[Dict[str, Any]]:
    """
    Generates realistic mock data records matching the field types and name patterns.
    """
    records = []
    
    # Common mock data pieces
    first_names = ["James", "Mary", "John", "Patricia", "Robert", "Jennifer", "Michael", "Linda", "William", "Elizabeth"]
    last_names = ["Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis", "Rodriguez", "Martinez"]
    products = ["Laptop Pro", "Wireless Mouse", "Mechanical Keyboard", "USB-C Hub", "4K Monitor", "Noise Cancelling Headphones", "Ergonomic Chair", "Desk Pad"]
    categories = ["Electronics", "Office Accessories", "Furniture", "Audio", "Computing"]
    statuses = ["PENDING", "COMPLETED", "FAILED", "PROCESSING", "SHIPPED", "ACTIVE", "INACTIVE"]
    
    for i in range(1, count + 1):
        record: Dict[str, Any] = {}
        for col in columns:
            name = col["name"].lower()
            col_type = col["type"].upper()
            is_pk = col.get("primary_key", False)
            
            # Check for explicitly mapped mock overrides
            override = col.get("mock_override")
            if override and override != "default":
                if override == "first_name":
                    record[col["name"]] = random.choice(first_names)
                elif override == "last_name":
                    record[col["name"]] = random.choice(last_names)
                elif override == "full_name":
                    record[col["name"]] = f"{random.choice(first_names)} {random.choice(last_names)}"
                elif override == "email":
                    record[col["name"]] = f"{random.choice(first_names).lower()}.{random.choice(last_names).lower()}{i}@example.com"
                elif override == "username":
                    record[col["name"]] = f"{random.choice(first_names).lower()}_{i}"
                elif override == "phone":
                    record[col["name"]] = f"+1-555-019-{i:04d}"
                elif override == "address":
                    record[col["name"]] = f"{100 + i} Developer Lane, Tech City"
                elif override == "uuid":
                    record[col["name"]] = f"3d9a7c{i:02d}-4f2a-8b9c-1234-56789abcdef0"
                elif override == "product":
                    record[col["name"]] = random.choice(products)
                elif override == "category":
                    record[col["name"]] = random.choice(categories)
                elif override == "status":
                    record[col["name"]] = random.choice(statuses)
                elif override == "token":
                    record[col["name"]] = f"TOK-{random.choice(['A','B','C','D'])}{random.randint(1000, 9999)}-{i:02d}"
                elif override == "currency":
                    record[col["name"]] = f"{random.choice(['$', '€', '£'])}{random.randint(10, 500)}.{random.randint(10, 99)}"
                elif override == "age":
                    record[col["name"]] = random.randint(18, 75)
                elif override == "quantity":
                    record[col["name"]] = random.randint(1, 10)
                elif override == "year":
                    record[col["name"]] = random.randint(2020, 2026)
                elif override == "price":
                    record[col["name"]] = round(random.uniform(9.99, 499.99), 2)
                elif override == "rating":
                    record[col["name"]] = round(random.uniform(3.5, 5.0), 1)
                elif override == "boolean":
                    record[col["name"]] = random.choice([True, False])
                elif override == "date":
                    record[col["name"]] = (datetime.now() - timedelta(days=i)).date().isoformat()
                elif override == "datetime":
                    record[col["name"]] = (datetime.now() - timedelta(days=i, hours=random.randint(0, 23))).isoformat()
                else:
                    record[col["name"]] = f"Val_{i}"
                continue

            # 1. Primary Key sequential generation
            if is_pk and ("INT" in col_type or "SERIAL" in col_type or "NUM" in col_type):
                record[col["name"]] = i
                continue
            
            # 2. String/Varchar columns
            if "VARCHAR" in col_type or "TEXT" in col_type or "STRING" in col_type or "CHAR" in col_type:
                if is_pk:
                    record[col["name"]] = f"ID-{1000 + i}"
                elif "email" in name:
                    fn = random.choice(first_names).lower()
                    ln = random.choice(last_names).lower()
                    record[col["name"]] = f"{fn}.{ln}{i}@example.com"
                elif "name" in name:
                    if "product" in name:
                        record[col["name"]] = random.choice(products)
                    else:
                        record[col["name"]] = f"{random.choice(first_names)} {random.choice(last_names)}"
                elif "username" in name or "user_name" in name:
                    record[col["name"]] = f"{random.choice(first_names).lower()}_{i}"
                elif "phone" in name or "tel" in name:
                    record[col["name"]] = f"+1-555-019-{i:04d}"
                elif "status" in name:
                    record[col["name"]] = random.choice(statuses)
                elif "category" in name:
                    record[col["name"]] = random.choice(categories)
                elif "address" in name:
                    record[col["name"]] = f"{100 + i} Developer Lane, Tech City"
                elif "uuid" in name or "guid" in name:
                    record[col["name"]] = f"3d9a7c{i:02d}-4f2a-8b9c-1234-56789abcdef0"
                else:
                    record[col["name"]] = f"Mock_{col['name']}_{i}"
            
            # 3. Numeric columns
            elif "INT" in col_type or "INTEGER" in col_type or "BIGINT" in col_type or "SMALLINT" in col_type:
                if "age" in name:
                    record[col["name"]] = random.randint(18, 75)
                elif "quantity" in name or "qty" in name or "count" in name:
                    record[col["name"]] = random.randint(1, 10)
                elif "year" in name:
                    record[col["name"]] = random.randint(2020, 2026)
                else:
                    record[col["name"]] = random.randint(100, 1000)
            
            # 4. Floating-point columns
            elif "FLOAT" in col_type or "DOUBLE" in col_type or "DECIMAL" in col_type or "NUMERIC" in col_type or "REAL" in col_type:
                if "price" in name or "amount" in name or "cost" in name or "total" in name:
                    record[col["name"]] = round(random.uniform(9.99, 499.99), 2)
                elif "rating" in name or "score" in name:
                    record[col["name"]] = round(random.uniform(3.5, 5.0), 1)
                else:
                    record[col["name"]] = round(random.uniform(0.0, 100.0), 2)
            
            # 5. Boolean columns
            elif "BOOL" in col_type:
                record[col["name"]] = random.choice([True, False])
                
            # 6. DateTime / Date columns
            elif "DATETIME" in col_type or "TIMESTAMP" in col_type:
                # generate dates starting from now and going back
                dt = datetime.now() - timedelta(days=i, hours=random.randint(0, 23))
                record[col["name"]] = dt.isoformat()
            elif "DATE" in col_type:
                dt = datetime.now() - timedelta(days=i)
                record[col["name"]] = dt.date().isoformat()
            
            # 7. Fallback
            else:
                record[col["name"]] = f"Value_{i}"
                
        records.append(record)
        
    return records
