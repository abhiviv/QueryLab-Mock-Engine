import os
from sqlalchemy import create_engine, Column, Integer, String, Boolean, Float, DateTime, MetaData, Table
from datetime import datetime

def setup_test_database():
    # Target path inside the project backend directory
    db_dir = os.path.dirname(os.path.abspath(__file__))
    db_path = os.path.join(db_dir, "test_db.sqlite")
    
    # SQLite connection URL
    connection_url = f"sqlite:///{db_path}"
    print(f"Creating local SQLite test database at: {db_path}")
    print(f"SQLAlchemy URL: sqlite:///{db_path.replace(os.sep, '/')}")
    
    engine = create_engine(connection_url)
    metadata = MetaData()
    
    # 1. Users Table Schema
    Table(
        'users', metadata,
        Column('id', Integer, primary_key=True, autoincrement=True),
        Column('username', String(50), nullable=False),
        Column('full_name', String(100), nullable=True),
        Column('email', String(120), nullable=False),
        Column('is_active', Boolean, default=True),
        Column('created_at', DateTime, default=datetime.utcnow)
    )
    
    # 2. Products Table Schema
    Table(
        'products', metadata,
        Column('product_id', Integer, primary_key=True, autoincrement=True),
        Column('product_name', String(100), nullable=False),
        Column('sku_code', String(30), nullable=False),
        Column('unit_price', Float, nullable=False),
        Column('quantity_in_stock', Integer, default=0),
        Column('updated_at', DateTime, default=datetime.utcnow)
    )
    
    metadata.create_all(engine)
    print("Database structures populated successfully!")

if __name__ == "__main__":
    setup_test_database()
