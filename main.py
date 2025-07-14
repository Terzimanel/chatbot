from fastapi import FastAPI
from pydantic import BaseModel
import requests
import re

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

def smart_filter_schema(schema: str, question: str) -> str:
    """
    Essaie d'extraire uniquement les tables pertinentes du schema
    en fonction de la question.
    """
    table_blocks = re.split(r'(?m)^\d+\.\s+', schema)
    table_names = []
    blocks_by_name = {}

    for block in table_blocks[1:]:
        lines = block.strip().splitlines()
        if not lines:
            continue
        header = lines[0]
        table_name = header.split()[0].replace('"','')
        table_names.append(table_name.lower())
        blocks_by_name[table_name.lower()] = f"{header}\n" + "\n".join(lines[1:])

    print(f"✅ Tables détectées : {table_names}")

    question_words = set(w.lower().strip(" ,.!?") for w in question.split() if len(w) > 2)
    print(f"✅ Mots de la question : {question_words}")

    matches = []
    for table in table_names:
        if any(word in table for word in question_words):
            matches.append(table)

    if matches:
        print(f"✅ Tables retenues : {matches}")
        return "\n\n".join(blocks_by_name[m] for m in matches)

    print("⚠️ Aucun match trouvé, retour complet")
    return schema

@app.post("/generate-sql")
async def generate_sql(request: PromptRequest):
    # Choisir le schema fourni ou celui chargé au démarrage
    raw_schema = request.schema if request.schema else SCHEMA_CONTENT

    # Filtrage intelligent pour réduire la taille
    schema_to_use = smart_filter_schema(raw_schema, request.user_question)

    # Construction du prompt allégé
    prompt = f"""
Générez une requête SQL PostgreSQL répondant à cette question :

"{request.user_question}"

Utilisez uniquement les tables et colonnes suivantes :

{schema_to_use}

Consignes :
- Répondez uniquement avec la requête SQL valide (commençant par SELECT ou WITH), sans explication ni format Markdown.
- Ne pas inventer de colonnes ni de tables.
- Si c'est impossible, répondez : Erreur : impossible de générer.
"""

    print(f"✅ Longueur du prompt final : {len(prompt)} caractères")

    try:
        response = requests.post(
            "http://127.0.0.1:11434/api/generate",
            json={
                "model": "mistral",
                "prompt": prompt,
                "stream": False
            },
            timeout=300
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
        print(f"✅ Longueur du prompt texte : {len(request.prompt)} caractères")

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
