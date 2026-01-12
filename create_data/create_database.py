import os
import importlib
from db.database import engine
from models.base import Base

# 自动import models目录下所有模型，确保Base.metadata.tables完整
models_dir = os.path.join(os.path.dirname(__file__), '..', 'models')
for fname in os.listdir(models_dir):
    if fname.endswith('.py') and not fname.startswith('__'):
        importlib.import_module(f"models.{fname[:-3]}")

# 获取所有表的建表SQL
sql=''
with engine.connect() as conn:
    for table in Base.metadata.sorted_tables:
        sql = str(table.compile(dialect=engine.dialect))
        sql+=sql + ";\n"
print(sql)
with open('create_database.sql', 'w',encoding='utf-8') as f:
    f.write(sql)
