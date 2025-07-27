from ..llm.gemini_sql_generator import generate_sql_from_nl

def generate_sql_query(user_query, schema):
    # Prepare prompt including schema + user query
    prompt = f"""
You are an expert SQL generator. Based on this schema:
{schema}

Generate a valid SQL SELECT query for:
{user_query}

Only use tables and columns available in the schema.
"""
    # Call Gemini API with prompt and get SQL
    sql = generate_sql_from_nl(prompt)
    return sql

def convert_result_to_natural_language(question, rows):
    if not rows:
        return f"Sorry, no data was found for: '{question}'."

    try:
        readable_rows = []
        for row in rows:
            # Convert each row dict into a sentence like: "John (30 years old, from USA)"
            sentence_parts = []
            for k, v in row.items():
                sentence_parts.append(f"{k.replace('_', ' ').capitalize()}: {v}")
            readable_rows.append(" | ".join(sentence_parts))

        if len(readable_rows) == 1:
            return f"Here is the result for your question: '{question}':\n{readable_rows[0]}"
        else:
            return f"Here are the results for: '{question}':\n" + "\n".join(readable_rows)

    except Exception as e:
        return f"Data fetched successfully, but formatting failed: {str(e)}"
