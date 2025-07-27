from sqlalchemy import create_engine, text
engine = create_engine("postgresql://mohanmanjhi@localhost:5432/sales_analytics")

with engine.connect() as conn:
    result = conn.execute(text("SELECT * FROM users LIMIT 1"))
    for row in result:
        print(row)
