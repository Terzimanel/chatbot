
# from fastapi import FastAPI
# from pydantic import BaseModel
# import requests

# app = FastAPI()

# # Chargement du schéma une fois au démarrage
# SCHEMA_CONTENT = ""

# @app.on_event("startup")
# async def startup_event():
#     global SCHEMA_CONTENT
#     try:
#         with open("schema.txt", "r", encoding="utf-8") as f:
#             SCHEMA_CONTENT = f.read()
#             print("✅ Schéma chargé")
#     except Exception as e:
#         print(f"❌ Erreur chargement schéma : {str(e)}")

# class PromptRequest(BaseModel):
#     user_question: str
#     schema: str = ""

# @app.post("/generate-sql")
# async def generate_sql(request: PromptRequest):
#     schema_to_use = request.schema if request.schema else SCHEMA_CONTENT
#     prompt = f"""
# Vous êtes un assistant IA qui génère des requêtes SQL PostgreSQL.
# Voici le schéma de la base (avec noms exacts entre guillemets) :

# {schema_to_use}

# L'utilisateur demande : "{request.user_question}"

# Générez uniquement la requête SQL exécutable, sans explication, sans format Markdown.
# Commencez par SELECT ou WITH uniquement.
# Utilisez les noms de tables et colonnes EXACTEMENT comme indiqués dans le schéma (avec guillemets doubles).
# Si la requête est impossible, répondez avec : Erreur : impossible de générer.
# """

#     try:
#         response = requests.post(
#             "http://127.0.0.1:11435/api/generate",
#             json={
#                 "model": "mistral",  # ou deepseek selon le modèle téléchargé
#                 "prompt": prompt,
#                 "stream": False
#             },
#             timeout=300
#         )
#         response.raise_for_status()
#         result = response.json().get("response", "").strip()
#         print("🧠 Réponse brute LLM:\n", result)

#         sql = extract_sql(result)
#         if not sql:
#             return {"sql": "", "error": result or "Aucune requête SQL détectée."}
        
#         return {"sql": sql, "error": ""}
    
#     except requests.RequestException as e:
#         print("🧠 Erreur réseau Ollama:", str(e))
#         return {"sql": "", "error": f"Erreur Ollama : {str(e)}"}
#     except Exception as e:
#         print("🧠 Erreur générale:", str(e))
#         return {"sql": "", "error": f"Erreur FastAPI : {str(e)}"}

# def extract_sql(text: str) -> str:
#     lines = text.strip().splitlines()
#     sql_lines = []
#     started = False
#     for line in lines:
#         if "select" in line.lower() or "with" in line.lower():
#             started = True
#         if started:
#             sql_lines.append(line)
#         if ";" in line:
#             break
#     sql = " ".join(sql_lines).strip()
#     return sql if sql.lower().startswith(("select", "with")) else ""
from fastapi import FastAPI
from pydantic import BaseModel
import requests

app = FastAPI()

# Chargement du schéma une fois au démarrage
SCHEMA_CONTENT = ""

@app.on_event("startup")
async def startup_event():
    global SCHEMA_CONTENT
    try:
        with open("schema.txt", "r", encoding="utf-8") as f:
            SCHEMA_CONTENT = f.read()
            print("✅ Schéma chargé")
    except Exception as e:
        print(f"❌ Erreur chargement schéma : {str(e)}")

class PromptRequest(BaseModel):
    user_question: str
    schema: str = ""

class TextRequest(BaseModel):
    prompt: str

@app.post("/generate-sql")
async def generate_sql(request: PromptRequest):
    schema_to_use = request.schema if request.schema else SCHEMA_CONTENT
    prompt = f"""
Vous êtes un assistant IA qui génère des requêtes SQL PostgreSQL.
Voici le schéma de la base (avec noms exacts entre guillemets) :

{schema_to_use}

L'utilisateur demande : "{request.user_question}"

Consignes strictes :
- Générez uniquement la requête SQL exécutable, sans explication ni format Markdown.
- Commencez par SELECT ou WITH uniquement.
- Utilisez exactement les noms de colonnes et de tables du schéma fourni, en respectant les guillemets doubles s'ils sont présents.
- ❌ N'inventez jamais de colonne. Si une colonne n'est pas dans le schéma, ne l'utilisez pas.
- Si la requête est impossible, répondez avec : Erreur : impossible de générer.
"""

    try:
        response = requests.post(
            "http://127.0.0.1:11434/api/generate",
            json={
                "model": "mistral",
                "prompt": prompt,
                "stream": False
            },
            timeout=600
        )
        response.raise_for_status()
        result = response.json().get("response", "").strip()
        print("🧠 Réponse brute LLM:\n", result)

        sql = extract_sql(result)
        if not sql:
            return {"sql": "", "error": result or "Aucune requête SQL détectée."}
        
        return {"sql": sql, "error": ""}
    
    except requests.RequestException as e:
        print("🧠 Erreur réseau Ollama:", str(e))
        return {"sql": "", "error": f"Erreur Ollama : {str(e)}"}
    except Exception as e:
        print("🧠 Erreur générale:", str(e))
        return {"sql": "", "error": f"Erreur FastAPI : {str(e)}"}

@app.post("/generate-text")
async def generate_text(request: TextRequest):
    try:
        response = requests.post(
            "http://127.0.0.1:11434/api/generate",
            json={
                "model": "mistral",
                "prompt": request.prompt,
                "stream": False
            },
            timeout=300
        )
        response.raise_for_status()
        result = response.json().get("response", "").strip()
        print("🧠 Réponse brute LLM (texte):\n", result)
        return {"text": result, "error": ""}
    
    except requests.RequestException as e:
        print("🧠 Erreur réseau Ollama:", str(e))
        return {"text": "", "error": f"Erreur Ollama : {str(e)}"}
    except Exception as e:
        print("🧠 Erreur générale:", str(e))
        return {"text": "", "error": f"Erreur FastAPI : {str(e)}"}

def extract_sql(text: str) -> str:
    lines = text.strip().splitlines()
    sql_lines = []
    started = False
    for line in lines:
        if "select" in line.lower() or "with" in line.lower():
            started = True
        if started:
            sql_lines.append(line)
        if ";" in line:
            break
    sql = " ".join(sql_lines).strip()
    return sql if sql.lower().startswith(("select", "with")) else ""