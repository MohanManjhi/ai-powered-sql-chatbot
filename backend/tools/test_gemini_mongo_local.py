import ast, inspect, textwrap
from pathlib import Path

p = Path(__file__).parents[1] / 'app' / 'llm' / 'gemini_mongo_generator.py'
source = p.read_text()
module = ast.parse(source)

# Find the function definition node
func_node = None
for node in module.body:
    if isinstance(node, ast.FunctionDef) and node.name == 'generate_mongo_query_from_nl':
        func_node = node
        break

if not func_node:
    print('Function not found')
    raise SystemExit(1)

# Create a new Module with helper stub and the function
stub_src = 'def _default_db_from_env():\n    return None\n\n'
func_src = ast.get_source_segment(source, func_node)
final_src = stub_src + func_src + '''

# Tests
queries = [
    'Show me all images',
    'Find images older than 5',
    "Get photos with filename 'car.jpg'",
    'List users in the userdb database',
]
for q in queries:
    print('\nQuery:', q)
    print(generate_mongo_query_from_nl(q))
'''

# Execute in isolated namespace
ns = {}
exec(final_src, ns)
