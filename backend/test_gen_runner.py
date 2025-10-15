from app.llm.gemini_mongo_generator import generate_mongo_query_from_nl

questions = [
    "Find images where name is nano",
    "Show me all images for filename 'tata'",
    "Get images named \"nano\" in the cardb database",
    "Return images with description containing red",
    "How many images for model tata",
    "Show me the first 10 images sorted by created_at",
]

for q in questions:
    print('Q:', q)
    print('->', generate_mongo_query_from_nl(q))
    print()
